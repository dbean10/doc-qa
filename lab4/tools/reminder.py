"""
lab4/tools/reminder.py

Reminder creation tool.
Production replacement: swap _store_reminder() to write to Firestore,
a task queue, or a calendar API. Validation and error contract stay identical.

In this simulation reminders are stored in an in-memory list so the chatbot
can display them with /reminders during a session. A real implementation
would persist to a database and integrate with a notification system.
"""

from __future__ import annotations

import uuid
from datetime import datetime


# ---------------------------------------------------------------------------
# In-memory store (session-scoped — resets on restart)
# ---------------------------------------------------------------------------

_reminders: list[dict] = []


# ---------------------------------------------------------------------------
# Public tool function
# ---------------------------------------------------------------------------

def create_reminder(text: str, time: str) -> dict:
    """
    Create a reminder for the user.

    Returns a dict — never raises.

    Args:
        text: What to remind the user about.
        time: Natural language time string, e.g. "tomorrow at 9am".

    Returns:
        On success: {"error": False, "id": str, "text": str, "time": str,
                     "created_at": str}
        On failure: {"error": True, "message": str}
    """
    # --- Morgan check 1: types ---
    if not isinstance(text, str):
        return {
            "error": True,
            "message": f"text must be a string, got {type(text).__name__}",
        }
    if not isinstance(time, str):
        return {
            "error": True,
            "message": f"time must be a string, got {type(time).__name__}",
        }

    # --- Morgan check 2: empty / whitespace ---
    text = text.strip()
    if not text:
        return {"error": True, "message": "reminder text cannot be empty"}

    time = time.strip()
    if not time:
        return {"error": True, "message": "reminder time cannot be empty"}

    # --- Morgan check 3: length bounds ---
    if len(text) > 500:
        return {"error": True, "message": "reminder text too long (max 500 chars)"}
    if len(time) > 200:
        return {"error": True, "message": "time string too long (max 200 chars)"}

    return _store_reminder(text, time)


def get_all_reminders() -> list[dict]:
    """Return all reminders created this session. Used by /reminders command."""
    return list(_reminders)


def clear_reminders() -> None:
    """Clear all reminders. Used in tests to reset state."""
    _reminders.clear()


# ---------------------------------------------------------------------------
# Internal implementation (swap this for a real persistence layer)
# ---------------------------------------------------------------------------

def _store_reminder(text: str, time: str) -> dict:
    """
    Store a reminder in the in-memory list.

    Production replacement:
        db = firestore.Client()
        doc_ref = db.collection("reminders").document()
        reminder = {
            "id": doc_ref.id,
            "text": text,
            "time": time,
            "created_at": datetime.utcnow().isoformat(),
            "user_id": current_user_id,   # from session context
            "notified": False,
        }
        doc_ref.set(reminder)
        return {"error": False, **reminder}
    """
    reminder = {
        "error": False,
        "id": str(uuid.uuid4())[:8],
        "text": text,
        "time": time,
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
    _reminders.append(reminder)
    return reminder
