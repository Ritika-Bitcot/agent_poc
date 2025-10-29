"""Data loader for mock data from JSON files."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class DataLoader:
    """Loads mock data from JSON files."""

    def __init__(self):
        """Initialize the data loader."""
        self.data_dir = Path(__file__).parent
        self._account_data: Optional[Dict[str, Any]] = None
        self._facility_data: Optional[Dict[str, Any]] = None
        self._notes_data: Optional[Dict[str, Any]] = None

    def _load_json_file(self, filename: str) -> Dict[str, Any]:
        """Load JSON data from a file."""
        file_path = self.data_dir / filename
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            print(f"Error loading {filename}: {e}")
            return {}

    def get_account_data(self) -> Dict[str, Any]:
        """Get account data."""
        if self._account_data is None:
            self._account_data = self._load_json_file("account_data.json")
        return self._account_data

    def get_facility_data(self) -> Dict[str, Any]:
        """Get facility data."""
        if self._facility_data is None:
            self._facility_data = self._load_json_file("facility_data.json")
        return self._facility_data

    def get_notes_data(self) -> Dict[str, Any]:
        """Get notes data."""
        if self._notes_data is None:
            self._notes_data = self._load_json_file("notes_data.json")
        return self._notes_data

    def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account data by account ID."""
        account_data = self.get_account_data()
        account_overview = account_data.get("account_overview", [])

        for account in account_overview:
            if account.get("account_id") == account_id:
                return account
        return None

    def get_facility_by_id(self, facility_id: str) -> Optional[Dict[str, Any]]:
        """Get facility data by facility ID."""
        facility_data = self.get_facility_data()
        facility_overview = facility_data.get("facility_overview", [])

        for facility in facility_overview:
            if facility.get("id") == facility_id:
                return facility
        return None

    def get_facilities_by_account_id(self, account_id: str) -> List[Dict[str, Any]]:
        """Get all facilities for a given account ID."""
        facility_data = self.get_facility_data()
        facility_overview = facility_data.get("facility_overview", [])

        facilities = []
        for facility in facility_overview:
            if facility.get("account_id") == account_id:
                facilities.append(facility)
        return facilities

    def get_notes_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """Get notes data by user ID."""
        notes_data = self.get_notes_data()
        return notes_data.get(str(user_id), [])

    def save_note(self, user_id: str, note: Dict[str, Any]) -> bool:
        """Save a note for a user to notes_data.json."""
        try:
            # Get current notes data (may be cached)
            notes_data = self.get_notes_data()
            user_id_str = str(user_id)

            # Initialize user's notes list if it doesn't exist
            if user_id_str not in notes_data:
                notes_data[user_id_str] = []

            # Add the new note
            notes_data[user_id_str].append(note)

            # Save back to file
            file_path = self.data_dir / "notes_data.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(notes_data, f, indent=2)
                f.flush()  # Ensure data is written to disk

            # Invalidate cache to ensure fresh data on next read
            self._notes_data = None

            return True
        except Exception as e:
            print(f"Error saving note to notes_data.json: {e}")
            return False


# Global data loader instance
_data_loader: Optional[DataLoader] = None


def get_data_loader() -> DataLoader:
    """Get the global data loader instance."""
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader()
    return _data_loader
