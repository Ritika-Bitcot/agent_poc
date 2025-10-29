"""Response models for the agent API."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AccountOverview(BaseModel):
    """Account overview data model."""

    account_id: str
    name: str
    status: str
    is_tna: bool
    created_at: datetime
    pricing_model: str
    address_line1: str
    address_line2: str
    address_city: str
    address_state: str
    address_postal_code: str
    address_country: str
    total_amount_due: float
    total_amount_due_this_week: float
    current_balance: int
    pending_balance: int
    current_tier: str
    next_tier: str
    points_to_next_tier: int
    quarter_end_date: datetime
    free_vials_available: int
    rewards_required_for_next_free_vial: int
    rewards_redeemed_towards_next_free_vial: int
    rewards_status: str
    rewards_updated_at: datetime
    evolux_level: str


class FacilityOverview(BaseModel):
    """Facility overview data model."""

    id: str
    name: str
    status: str
    has_signed_medical_liability_agreement: bool
    medical_license_id: str
    medical_license_state: str
    medical_license_number: str
    medical_license_involvement: str
    medical_license_expiration_date: datetime
    medical_license_is_expired: bool
    medical_license_status: str
    medical_license_owner_first_name: str
    medical_license_owner_last_name: str
    account_id: str
    account_name: str
    account_status: str
    account_has_signed_financial_agreement: bool
    account_has_accepted_jet_terms: bool
    shipping_address_line1: str
    shipping_address_line2: str
    shipping_address_city: str
    shipping_address_state: str
    shipping_address_zip: str
    shipping_address_commercial: bool
    sponsored: bool
    agreement_status: str
    agreement_signed_at: datetime
    agreement_type: str


class NoteOverview(BaseModel):
    """Note overview data model."""

    id: str
    user_id: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class RewardsOverview(BaseModel):
    """Rewards overview data model."""

    current_tier: str
    next_tier: str
    points_to_next_tier: int
    total_points: int
    points_earned_this_quarter: int
    quarter_end_date: datetime
    free_vials_available: int
    rewards_required_for_next_free_vial: int
    rewards_redeemed_towards_next_free_vial: int


class OrderOverview(BaseModel):
    """Order overview data model."""

    order_id: str
    status: str
    total_amount: float
    created_at: datetime
    items: List[dict]


class AgentResponse(BaseModel):
    """Main response model for agent interactions."""

    conversation_id: str = Field(..., description="Unique conversation identifier")
    final_response: str = Field(
        ..., description="Human-friendly natural language response"
    )
    card_key: Literal[
        "account_overview", "facility_overview", "notes_overview", "other"
    ] = Field(..., description="UI card type for frontend rendering")
    account_overview: List[AccountOverview] = Field(default_factory=list)
    facility_overview: Optional[List[FacilityOverview]] = None
    note_overview: List[NoteOverview] = Field(default_factory=list)
    rewards_overview: Optional[RewardsOverview] = None
    order_overview: Optional[List[OrderOverview]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "c625fbc7-cc93-4a7e-841b-180872a9420a",
                "final_response": "Here is a summary of your account...",
                "card_key": "account_overview",
                "account_overview": [],
                "facility_overview": None,
                "note_overview": [],
                "rewards_overview": None,
                "order_overview": None,
            }
        }
