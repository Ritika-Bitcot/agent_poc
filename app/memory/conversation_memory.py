"""PostgreSQL-based conversation memory implementation."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage

from app.memory.database import (
    Conversation,
    ConversationMessage,
    SessionLocal,
    create_tables,
)


class PostgreSQLConversationMemory:
    """PostgreSQL-based conversation memory for multi-turn conversations."""

    def __init__(self, max_conversation_age_hours: int = 24):
        """
        Initialize PostgreSQL conversation memory.

        Args:
            max_conversation_age_hours: Maximum age of conversations to keep in memory
        """
        self.max_conversation_age_hours = max_conversation_age_hours
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

    def get_conversation_history(
        self, conversation_id: str, limit: int = 10
    ) -> List[BaseMessage]:
        """
        Get conversation history for a given conversation ID.

        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of recent messages to return

        Returns:
            List of recent messages
        """
        db = SessionLocal()
        try:
            # Update last accessed time
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if conversation:
                conversation.last_accessed = datetime.utcnow()
                db.commit()

            # Get recent messages
            messages = (
                db.query(ConversationMessage)
                .filter(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.created_at.desc())
                .limit(limit)
                .all()
            )

            # Convert to BaseMessage objects (simplified for now)
            result = []
            for msg in reversed(messages):  # Reverse to get chronological order
                # This is a simplified conversion - in practice you'd want to
                # properly reconstruct the specific message type
                result.append(msg.content)

            return result

        finally:
            db.close()

    def cleanup_old_conversations(self) -> int:
        """
        Clean up conversations older than max_conversation_age_hours.

        Returns:
            Number of conversations cleaned up
        """
        db = SessionLocal()
        try:
            cutoff_time = datetime.utcnow() - timedelta(
                hours=self.max_conversation_age_hours
            )

            # Mark old conversations as inactive
            old_conversations = (
                db.query(Conversation)
                .filter(
                    Conversation.last_accessed < cutoff_time,
                    Conversation.is_active,
                )
                .all()
            )

            for conversation in old_conversations:
                conversation.is_active = False

            db.commit()
            return len(old_conversations)

        finally:
            db.close()

    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored conversations.

        Returns:
            Dictionary with conversation statistics
        """
        db = SessionLocal()
        try:
            total_conversations = (
                db.query(Conversation).filter(Conversation.is_active).count()
            )
            total_messages = db.query(ConversationMessage).count()

            oldest_conversation = (
                db.query(Conversation)
                .filter(Conversation.is_active)
                .order_by(Conversation.created_at.asc())
                .first()
            )

            newest_conversation = (
                db.query(Conversation)
                .filter(Conversation.is_active)
                .order_by(Conversation.created_at.desc())
                .first()
            )

            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "oldest_conversation": (
                    oldest_conversation.created_at if oldest_conversation else None
                ),
                "newest_conversation": (
                    newest_conversation.created_at if newest_conversation else None
                ),
            }

        finally:
            db.close()

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a specific conversation.

        Args:
            conversation_id: ID of the conversation to delete

        Returns:
            True if conversation was deleted, False if not found
        """
        db = SessionLocal()
        try:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )

            if conversation:
                # Delete all messages first
                db.query(ConversationMessage).filter(
                    ConversationMessage.conversation_id == conversation_id
                ).delete()

                # Delete conversation
                db.delete(conversation)
                db.commit()
                return True

            return False

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
