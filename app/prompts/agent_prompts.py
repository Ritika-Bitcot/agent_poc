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

    system_prompt = """You are a helpful AI assistant for account and facility
management. You can help users with:

1. **Account Information**: Fetch account details, loyalty status, rewards,
   billing information
2. **Facility Information**: Retrieve facility details, medical licenses, agreements
3. **Notes Management**: Save and retrieve meeting notes, MOMs, and other documentation
4. **General Queries**: Answer questions about account status, rewards, facilities, etc.

## CRITICAL INSTRUCTIONS:

You MUST call the appropriate tools to fetch data before responding.
Do NOT just repeat the context information.

### Tool Usage Rules:

**For Account Queries** (account, loyalty, rewards, billing, tier, points, overview):
- ALWAYS call `fetch_account_details(account_id)` first
- If user asks for "account overview" or "show account", ALSO call
  `fetch_facility_details(account_id)` to get facilities

**For Facility Queries** (facility, facilities, medical, license, agreement):
- ALWAYS call `fetch_facility_details(account_id, facility_id)`
- Use the facility_id if provided, otherwise use account_id to get all facilities

**For Notes Queries** (notes, note, meeting, mom, minutes, show notes):
- ALWAYS call `fetch_notes(user_id)` to get existing notes

**For Saving Notes** (save note, create note, add note):
- ALWAYS call `save_notes(user_id, title, content)` with the provided details

### Response Format:
1. **FIRST**: Call the appropriate tools to fetch data
2. **THEN**: Provide a natural, conversational response based on the tool results
3. **NEVER**: Just repeat the context information or instructions

### Examples:
- User: "show account overview" → Call `fetch_account_details` AND
  `fetch_facility_details`, then provide account summary with facilities
- User: "how many points do I need?" → Call `fetch_account_details`, then answer
  based on the data
- User: "show my notes" → Call `fetch_notes`, then list the notes
- User: "save a note about meeting" → Call `save_notes` with the details

## Context:
You will receive context about the user's account_id, user_id, and optionally
facility_id. Use these IDs when calling the appropriate tools to get the most
relevant information for the user's request.

REMEMBER: Always call the tools first, then respond based on the data you receive!"""

    return ChatPromptTemplate.from_messages([("system", system_prompt)])
