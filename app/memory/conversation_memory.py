"""PostgreSQL-based conversation memory implementation."""

import json
import uuid
from datetime import datetime
from typing import Optional

from langchain_core.messages import BaseMessage

from app.memory.database import (
    Conversation,
    ConversationMessage,
    SessionLocal,
    create_tables,
)


class PostgreSQLConversationMemory:
    """PostgreSQL-based conversation memory for multi-turn conversations."""

    def __init__(self):
        """Initialize PostgreSQL conversation memory."""
        # Ensure tables exist
        create_tables()

    def get_or_create_conversation_id(
        self, user_id: str, provided_conversation_id: Optional[str] = None
    ) -> str:
        """
        Get existing conversation ID or create a new one.

        Args:
            user_id: User ID for the conversation
            provided_conversation_id: Optional conversation ID from request

        Returns:
            Conversation ID to use
        """
        db = SessionLocal()
        try:
            if provided_conversation_id:
                # Check if conversation exists and belongs to the user
                conversation = (
                    db.query(Conversation)
                    .filter(
                        Conversation.id == provided_conversation_id,
                        Conversation.user_id == user_id,
                        Conversation.is_active,
                    )
                    .first()
                )
                if conversation:
                    # Update last accessed time
                    conversation.last_accessed = datetime.utcnow()
                    db.commit()
                    return provided_conversation_id

            # Create new conversation
            conversation_id = str(uuid.uuid4())
            new_conversation = Conversation(
                id=conversation_id,
                user_id=user_id,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                message_count=0,
                is_active=True,
            )
            db.add(new_conversation)
            db.commit()
            return conversation_id

        finally:
            db.close()

    def add_message(self, conversation_id: str, message: BaseMessage) -> None:
        """
        Add a message to the conversation.

        Args:
            conversation_id: ID of the conversation
            message: Message to add
        """
        db = SessionLocal()
        try:
            # Update conversation metadata
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if conversation:
                conversation.last_accessed = datetime.utcnow()
                conversation.message_count += 1

            # Add message
            message_id = str(uuid.uuid4())
            message_type = getattr(message, "type", "unknown")
            content = getattr(message, "content", str(message))
            metadata = json.dumps(getattr(message, "additional_kwargs", {}))

            new_message = ConversationMessage(
                id=message_id,
                conversation_id=conversation_id,
                message_type=message_type,
                content=content,
                created_at=datetime.utcnow(),
                metadata=metadata,
            )
            db.add(new_message)
            db.commit()

        finally:
            db.close()


# Global conversation memory instance
_conversation_memory: Optional[PostgreSQLConversationMemory] = None


def get_conversation_memory() -> PostgreSQLConversationMemory:
    """Get the global conversation memory instance."""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = PostgreSQLConversationMemory()
    return _conversation_memory
