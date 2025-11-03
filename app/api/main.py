"""FastAPI main application."""

from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings

from app.agent import get_agent, process_agent_request
from app.memory import create_tables
from app.models import AgentRequest, AgentResponse


class Settings(BaseSettings):
    """Application settings."""

    openai_api_key: str = "dummy-key-for-testing"
    model_name: str = "gpt-4o-mini"
    debug: bool = False

    # Database settings
    database_url: Optional[str] = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "agent_poc_db"
    db_user: str = "username"
    db_password: str = "password"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env


# Load settings
settings = Settings()

# Create FastAPI app
app = FastAPI(
    title="Agent POC API",
    description="Single-agent architecture with LangGraph and FastAPI",
    version="1.0.0",
    debug=settings.debug,
)


# Initialize database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    try:
        create_tables()
        print("✅ Database tables initialized successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize database tables: {e}")
        print(
            "   The application will continue but conversation memory "
            "may not work properly."
        )


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_agent_dependency():
    """Dependency to get the agent instance."""
    return get_agent(settings.openai_api_key)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agent POC API is running",
        "version": "1.0.0",
        "status": "healthy",
    }


@app.post("/chat", response_model=AgentResponse)
async def chat_with_agent(
    request: AgentRequest, agent=Depends(get_agent_dependency)
) -> AgentResponse:
    """
    Chat with the agent.

    This endpoint processes user messages and returns structured responses
    with conversation memory support.

    Note: All errors are handled by process_agent_request() and returned
    as AgentResponse instances for consistency.
    """
    # process_agent_request() handles all errors and returns AgentResponse
    return process_agent_request(
        agent=agent,
        text=request.text,
        user_id=request.user_id,
        account_id=request.account_id,
        facility_id=request.facility_id,
        conversation_id=request.conversation_id,
    )


if __name__ == "__main__":
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
