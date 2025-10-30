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

    system_prompt = """You are a helpful AI assistant for account, facility, and notes
management. Decide which tools to call based on the user's intent. Do not rely on
hardcoded rules; use the context and the user's query to choose tools and arguments.

Capabilities:
- Account Information: details, loyalty, rewards, billing, tiers, points
- Facility Information: facility details, medical licenses, agreements
- Notes: save new notes and fetch existing notes

Instructions:
- Read the user's query and the provided context (account_id, user_id, facility_id).
- Choose appropriate tools and arguments to satisfy the request.
- Then return a single JSON object that conforms to the response schema below.
- Include a clear human-friendly answer in the `final_response` field.

Response Schema (high-level):
- conversation_id: string
- final_response: string
- card_key: one of [account_overview, facility_overview, notes_overview, other]
- account_overview: array (optional)
- facility_overview: array (optional)
- note_overview: array (optional)
- rewards_overview: object (optional)
- order_overview: array (optional)

Formatting:
- Output only the JSON object, with no surrounding commentary.
- If no structured data applies, set arrays to [] and objects to null.
"""

    return ChatPromptTemplate.from_messages([("system", system_prompt)])
