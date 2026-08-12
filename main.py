"""
Entry point for the Render background worker.

Runs two things on the same asyncio event loop:
  1. A repeating job (PTB's JobQueue) that scans profiles, evaluates
     them with Groq, stores qualified leads, and notifies Telegram.
  2. The Telegram bot's own polling loop, listening for button presses
     (e.g. "Mark Contacted").

Start command on Render: `python main.py`. No port needs to be
exposed — background workers don't serve HTTP.
"""

# Loaded first, before importing local modules that read environment
# variables at import time (database.py, ai_evaluator.py, telegram_bot.py).
# Harmless in production: load_dotenv() never overrides variables
# Render already set, and does nothing if no .env file is present.
from dotenv import load_dotenv

load_dotenv()

import asyncio
import logging
import os

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

import database
import scraper
from ai_evaluator import evaluate_profile
from telegram_bot import handle_callback, send_lead_notification

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SCAN_INTERVAL_SECONDS = int(os.environ.get("SCAN_INTERVAL_SECONDS", "600"))


async def run_pipeline(context: ContextTypes.DEFAULT_TYPE) -> None:
    """One full scan: fetch profiles, skip already-visited ones, evaluate
    the rest, store + notify on qualified leads."""
    logger.info("Scan started")
    profiles = scraper.get_profiles()

    for profile in profiles:
        username = profile.get("username")
        platform = profile.get("platform")

        try:
            already_seen = await asyncio.to_thread(database.is_visited, username, platform)
            if already_seen:
                continue

            # Blocking network calls run in a thread so the bot stays
            # responsive to button presses while a scan is in progress.
            result = await asyncio.to_thread(evaluate_profile, profile)
            await asyncio.to_thread(database.mark_visited, username, platform)

            if result["qualified"]:
                lead_id = await asyncio.to_thread(
                    database.insert_qualified_lead, profile, result["reason"]
                )
                await send_lead_notification(context.bot, lead_id, profile, result["reason"])
                logger.info("Qualified lead: %s (%s)", username, platform)
            else:
                logger.info("Not qualified: %s (%s)", username, platform)

        except Exception:
            # Not marked visited on failure, so it's retried on the next scan.
            logger.exception(
                "Failed to process %s (%s), will retry next scan", username, platform
            )

    logger.info("Scan finished")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception while processing update: %s", update, exc_info=context.error)


def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(on_error)

    application.job_queue.run_repeating(
        run_pipeline, interval=SCAN_INTERVAL_SECONDS, first=5
    )

    logger.info("Worker starting — scanning every %s seconds", SCAN_INTERVAL_SECONDS)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
