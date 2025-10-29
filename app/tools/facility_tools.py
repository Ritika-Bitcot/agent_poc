"""Facility-related tools for the agent."""

from typing import Any, Dict

from langchain_core.tools import tool

from app.data import get_data_loader


@tool
def fetch_facility_details(account_id: str, facility_id: str = None) -> Dict[str, Any]:
    """
    Retrieve facility related information for a given account ID.
    If facility_id is provided, returns specific facility details.
    If facility_id is not provided, returns all facilities for the account.

    Args:
        account_id: The account ID associated with the facility
        facility_id: Optional facility ID to fetch specific facility details

    Returns:
        Dictionary containing facility overview data
    """
    data_loader = get_data_loader()

    if facility_id:
        # Fetch specific facility
        facility_data = data_loader.get_facility_by_id(facility_id)
        if facility_data:
            return {"facility_overview": [facility_data]}
        else:
            return {"facility_overview": []}
    else:
        # Fetch all facilities for the account
        facilities = data_loader.get_facilities_by_account_id(account_id)
        return {"facility_overview": facilities}
