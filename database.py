"""
Supabase access layer.

Uses the service_role key, since this runs entirely server-side on
Render — never expose that key to a client/browser context.
"""

import os

from supabase import Client, create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def is_visited(username: str, platform: str) -> bool:
    """True if this (username, platform) pair has already been evaluated."""
    response = (
        supabase.table("visited_accounts")
        .select("id")
        .eq("username", username)
        .eq("platform", platform)
        .limit(1)
        .execute()
    )
    return len(response.data) > 0


def mark_visited(username: str, platform: str) -> None:
    """Records that this profile has been evaluated, regardless of outcome."""
    supabase.table("visited_accounts").insert(
        {"username": username, "platform": platform}
    ).execute()


def insert_qualified_lead(profile: dict, ai_reasoning: str) -> int:
    """Stores a qualified lead and returns its new row id."""
    response = (
        supabase.table("qualified_leads")
        .insert(
            {
                "username": profile.get("username"),
                "platform": profile.get("platform"),
                "followers_count": profile.get("followers_count"),
                "bio": profile.get("bio"),
                "ai_reasoning": ai_reasoning,
                "status": "pending",
            }
        )
        .execute()
    )
    return response.data[0]["id"]


def update_lead_status(lead_id: int, status: str) -> None:
    """Updates a lead's status, e.g. to 'contacted' after manual outreach."""
    supabase.table("qualified_leads").update({"status": status}).eq(
        "id", lead_id
    ).execute()
