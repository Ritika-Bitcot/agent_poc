"""Notes-related tools for the agent."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from langchain_core.tools import tool

from app.data import get_data_loader


@tool
def save_notes(user_id: str, title: str, content: str) -> Dict[str, Any]:
    """
    Save MOM (Minutes of Meeting) or notes given by user.

    Args:
        user_id: The user ID who is saving the notes
        title: Title of the notes
        content: Content of the notes

    Returns:
        Dictionary containing the saved note information
    """
    note_id = str(uuid.uuid4())
    current_time = datetime.now().isoformat()

    note_data = {
        "id": note_id,
        "user_id": user_id,
        "title": title,
        "content": content,
        "created_at": current_time,
        "updated_at": current_time,
    }

    # Save to JSON file using data loader
    data_loader = get_data_loader()
    success = data_loader.save_note(user_id, note_data)

    if success:
        return {
            "success": True,
            "note_id": note_id,
            "message": f"Note '{title}' saved successfully",
            "note": note_data,
        }
    else:
        return {
            "success": False,
            "message": "Failed to save note",
            "note": note_data,
        }


@tool
def fetch_notes(
    user_id: str, date: Optional[str] = None, limit: int = 5
) -> Dict[str, Any]:
    """
    Retrieve notes based on user_id, date, or last N notes.

    Args:
        user_id: The user ID to fetch notes for
        date: Optional date filter (YYYY-MM-DD format)
        limit: Maximum number of notes to return (default: 5)

    Returns:
        Dictionary containing the fetched notes
    """
    data_loader = get_data_loader()
    user_notes = data_loader.get_notes_by_user_id(user_id)

    if not user_notes:
        return {"note_overview": [], "message": "No notes found for this user"}

    # Filter by date if provided
    if date:
        filtered_notes = [
            note for note in user_notes if note.get("created_at", "").startswith(date)
        ]
    else:
        filtered_notes = user_notes

    # Sort by created_at (newest first) and limit
    filtered_notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    limited_notes = filtered_notes[:limit]

    return {
        "success": True,
        "note_overview": limited_notes,
        "total_count": len(limited_notes),
        "message": f"Retrieved {len(limited_notes)} notes for user {user_id}",
    }
