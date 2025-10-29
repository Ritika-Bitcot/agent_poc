"""FastAPI main application."""

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings

from app.agent import get_agent, process_agent_request
from app.memory import create_tables, get_conversation_memory
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
    allow_origins=["*"],  # Configure appropriately for production
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agent-poc-api"}


@app.post("/chat", response_model=AgentResponse)
async def chat_with_agent(
    request: AgentRequest, agent=Depends(get_agent_dependency)
) -> AgentResponse:
    """
    Chat with the agent.

    This endpoint processes user messages and returns structured responses
    with conversation memory support.
    """
    try:
        # Process the request through the agent
        response = process_agent_request(
            agent=agent,
            text=request.text,
            user_id=request.user_id,
            account_id=request.account_id,
            facility_id=request.facility_id,
            conversation_id=request.conversation_id,
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )


@app.get("/conversations/{conversation_id}")
async def get_conversation_info(conversation_id: str):
    """Get information about a specific conversation."""
    try:
        conv_memory = get_conversation_memory()
        stats = conv_memory.get_conversation_stats()

        return {
            "conversation_id": conversation_id,
            "stats": stats,
            "message": "Conversation information retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving conversation info: {str(e)}"
        )


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a specific conversation."""
    try:
        conv_memory = get_conversation_memory()
        if conversation_id in conv_memory.conversation_metadata:
            del conv_memory.conversation_metadata[conversation_id]
            return {"message": f"Conversation {conversation_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting conversation: {str(e)}"
        )


@app.get("/conversations")
async def list_conversations():
    """List all conversations."""
    try:
        conv_memory = get_conversation_memory()
        stats = conv_memory.get_conversation_stats()

        return {
            "conversations": list(conv_memory.conversation_metadata.keys()),
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing conversations: {str(e)}"
        )


@app.post("/cleanup")
async def cleanup_old_conversations():
    """Clean up old conversations."""
    try:
        conv_memory = get_conversation_memory()
        cleaned_count = conv_memory.cleanup_old_conversations()

        return {
            "message": f"Cleaned up {cleaned_count} old conversations",
            "cleaned_count": cleaned_count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error cleaning up conversations: {str(e)}"
        )


@app.post("/postman", response_model=AgentResponse)
async def postman_chat(
    request: AgentRequest, agent=Depends(get_agent_dependency)
) -> AgentResponse:
    """
    Simplified chat endpoint that accepts the same format as /chat.

    This endpoint works with the same AgentRequest model, making it simpler
    to use with Postman or any other client.
    """
    try:
        # Process the request directly through the agent
        response = process_agent_request(
            agent=agent,
            text=request.text,
            user_id=request.user_id,
            account_id=request.account_id,
            facility_id=request.facility_id,
            conversation_id=request.conversation_id,
        )

        return response

    except Exception as e:
        # Return error response in the same format
        return AgentResponse(
            conversation_id=request.conversation_id or "error",
            final_response=f"Error processing request: {str(e)}",
            card_key="other",
            account_overview=[],
            facility_overview=None,
            note_overview=[],
            rewards_overview=None,
            order_overview=None,
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
