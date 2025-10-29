"""Request models for the agent API."""

from typing import Optional

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Request model for agent interactions."""

    text: str = Field(..., description="User's message or query")
    user_id: str = Field(..., description="Unique identifier for the user")
    title: str = Field(..., description="Title or context for the conversation")
    account_id: str = Field(..., description="Account ID for the user")
    facility_id: Optional[str] = Field(None, description="Optional facility ID")
    conversation_id: Optional[str] = Field(
        None, description="Optional conversation ID for multi-turn conversations"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "show account overview",
                "user_id": "kaushal.sethia.c@evolus.com",
                "title": "sample",
                "account_id": "A-011977763",
                "facility_id": "F-013203268",
                "conversation_id": "c625fbc7-cc93-4a7e-841b-180872a9420a",
            }
        }
