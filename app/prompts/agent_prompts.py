"""Agent prompt templates with structured output enforcement."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate


def get_response_schema() -> Dict[str, Any]:
    """Get the JSON schema for structured responses."""
    return {
        "type": "object",
        "properties": {
            "conversation_id": {
                "type": "string",
                "description": "Unique conversation identifier",
            },
            "final_response": {
                "type": "string",
                "description": "Human-friendly natural language response",
            },
            "card_key": {
                "type": "string",
                "enum": [
                    "account_overview",
                    "facility_overview",
                    "notes_overview",
                    "other",
                ],
                "description": "UI card type for frontend rendering",
            },
            "account_overview": {
                "type": "array",
                "items": {"$ref": "#/definitions/AccountOverview"},
                "description": "Account details if requested",
            },
            "facility_overview": {
                "type": "array",
                "items": {"$ref": "#/definitions/FacilityOverview"},
                "description": "Facility details if requested",
            },
            "note_overview": {
                "type": "array",
                "items": {"$ref": "#/definitions/NoteOverview"},
                "description": "Notes if requested",
            },
            "rewards_overview": {
                "type": "object",
                "description": "Rewards information if requested",
            },
            "order_overview": {
                "type": "array",
                "items": {"$ref": "#/definitions/OrderOverview"},
                "description": "Order information if requested",
            },
        },
        "required": ["conversation_id", "final_response", "card_key"],
        "definitions": {
            "AccountOverview": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "name": {"type": "string"},
                    "status": {"type": "string"},
                    "is_tna": {"type": "boolean"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "pricing_model": {"type": "string"},
                    "address_line1": {"type": "string"},
                    "address_line2": {"type": "string"},
                    "address_city": {"type": "string"},
                    "address_state": {"type": "string"},
                    "address_postal_code": {"type": "string"},
                    "address_country": {"type": "string"},
                    "total_amount_due": {"type": "number"},
                    "total_amount_due_this_week": {"type": "number"},
                    "current_balance": {"type": "integer"},
                    "pending_balance": {"type": "integer"},
                    "current_tier": {"type": "string"},
                    "next_tier": {"type": "string"},
                    "points_to_next_tier": {"type": "integer"},
                    "quarter_end_date": {"type": "string", "format": "date-time"},
                    "free_vials_available": {"type": "integer"},
                    "rewards_required_for_next_free_vial": {"type": "integer"},
                    "rewards_redeemed_towards_next_free_vial": {"type": "integer"},
                    "rewards_status": {"type": "string"},
                    "rewards_updated_at": {"type": "string", "format": "date-time"},
                    "evolux_level": {"type": "string"},
                },
            },
            "FacilityOverview": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "status": {"type": "string"},
                    "has_signed_medical_liability_agreement": {"type": "boolean"},
                    "medical_license_id": {"type": "string"},
                    "medical_license_state": {"type": "string"},
                    "medical_license_number": {"type": "string"},
                    "medical_license_involvement": {"type": "string"},
                    "medical_license_expiration_date": {
                        "type": "string",
                        "format": "date-time",
                    },
                    "medical_license_is_expired": {"type": "boolean"},
                    "medical_license_status": {"type": "string"},
                    "medical_license_owner_first_name": {"type": "string"},
                    "medical_license_owner_last_name": {"type": "string"},
                    "account_id": {"type": "string"},
                    "account_name": {"type": "string"},
                    "account_status": {"type": "string"},
                    "account_has_signed_financial_agreement": {"type": "boolean"},
                    "account_has_accepted_jet_terms": {"type": "boolean"},
                    "shipping_address_line1": {"type": "string"},
                    "shipping_address_line2": {"type": "string"},
                    "shipping_address_city": {"type": "string"},
                    "shipping_address_state": {"type": "string"},
                    "shipping_address_zip": {"type": "string"},
                    "shipping_address_commercial": {"type": "boolean"},
                    "sponsored": {"type": "boolean"},
                    "agreement_status": {"type": "string"},
                    "agreement_signed_at": {"type": "string", "format": "date-time"},
                    "agreement_type": {"type": "string"},
                },
            },
            "NoteOverview": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                },
            },
            "OrderOverview": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "status": {"type": "string"},
                    "total_amount": {"type": "number"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "items": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
    }


def get_agent_prompt() -> ChatPromptTemplate:
    """Get the main agent prompt template with structured output enforcement."""

    system_prompt = """You are a helpful AI assistant for account and
facility management. You can help users with:

1. **Account Information**: Fetch account details, loyalty status, rewards,
   billing information
2. **Facility Information**: Retrieve facility details, medical licenses,
   agreements
3. **Notes Management**: Save and retrieve meeting notes, MOMs, and other
   documentation
4. **General Queries**: Answer questions about account status, rewards,
   facilities, etc.

## How to Help Users:

- When users ask for account information, use the fetch_account_details tool
  with the account_id provided
- When users ask for facility information, use the fetch_facility_details tool
  with the facility_id
- When users ask about notes, use the fetch_notes tool with the user_id
- When users want to save notes, use the save_notes tool with the user_id,
  title, and content
- Answer questions naturally and helpfully based on the tool results you receive
- Be concise and professional in your responses

## Important:
- Use the available tools to fetch data when needed
- After calling tools, provide a clear, natural language response based on the results
- If you cannot find information, let the user know politely
- Do NOT try to format responses as JSON or structured data - just respond naturally
- Once you have the information from tools, answer the user's question directly"""

    return ChatPromptTemplate.from_messages([("system", system_prompt)])
