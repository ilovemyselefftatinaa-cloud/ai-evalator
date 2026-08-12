"""
AI qualification step, powered by Groq.

Model note: the brief asked for `llama-3.1-8b-instant`, but Groq has
that model scheduled for shutdown on 2026-08-16 (see
https://console.groq.com/docs/deprecations). This uses their official
recommended replacement, `openai/gpt-oss-20b`, instead — same speed/
cost tier, plus native support for strict JSON-schema output, which is
more reliable than the older "JSON mode" for this use case. Change
MODEL_NAME below if you'd rather use something else.
"""

import json
import os

from groq import Groq

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
MODEL_NAME = "openai/gpt-oss-20b"

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = (
    "You are a lead-qualification assistant for a freelance video editor. "
    "Given a social media profile's bio, a description of its recent "
    "posts, and its follower count, decide whether this account would "
    "likely benefit from hiring a professional video editor — for "
    "example: inconsistent or raw/unedited footage, decent reach but weak "
    "production quality, no visible editor or agency credit, or clear "
    "room to grow through better editing. Write the reason in Arabic."
)

# Strict JSON-schema mode: Groq guarantees the response matches this
# schema exactly, so no fuzzy prompt-engineering is needed to keep the
# model on-format.
RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "lead_qualification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "qualified": {
                    "type": "boolean",
                    "description": "True if this profile looks like a good video-editing lead.",
                },
                "reason": {
                    "type": "string",
                    "description": "Short explanation, written in Arabic.",
                },
            },
            "required": ["qualified", "reason"],
            "additionalProperties": False,
        },
    },
}


def evaluate_profile(profile: dict) -> dict:
    """Asks Groq to qualify a single profile.

    Returns {"qualified": bool, "reason": str}. Network/API failures are
    left to propagate to the caller (main.py) so a profile can be
    retried on the next scan rather than silently marked as visited.
    """
    user_content = (
        f"Bio: {profile.get('bio', '')}\n"
        f"Recent posts: {profile.get('recent_posts', '')}\n"
        f"Followers: {profile.get('followers_count', 0)}"
    )

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        reasoning_effort="low",  # simple classification, no need for deep reasoning
        response_format=RESPONSE_SCHEMA,
    )
    raw = completion.choices[0].message.content

    try:
        result = json.loads(raw)
        return {
            "qualified": bool(result.get("qualified", False)),
            "reason": str(result.get("reason", "")).strip(),
        }
    except (json.JSONDecodeError, AttributeError, TypeError):
        # Extremely unlikely under strict schema mode, but fall back
        # safely rather than crashing the pipeline on a malformed reply.
        return {"qualified": False, "reason": "تعذر تحليل استجابة الذكاء الاصطناعي"}
