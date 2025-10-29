"""Account-related tools for the agent."""

from typing import Any, Dict

from langchain_core.tools import tool

from app.data import get_data_loader


@tool
def fetch_account_details(account_id: str) -> Dict[str, Any]:
    """
    Retrieve account related information for a given account ID.

    Args:
        account_id: The account ID to fetch details for

    Returns:
        Dictionary containing account overview data
    """
    data_loader = get_data_loader()
    account_data = data_loader.get_account_by_id(account_id)

    if account_data:
        return {"account_overview": [account_data]}
    else:
        # Return empty if account not found
        return {"account_overview": []}
