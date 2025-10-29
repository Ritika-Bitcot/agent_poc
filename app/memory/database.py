"""Database configuration and models for conversation memory."""

from datetime import datetime
from typing import Optional

from pydantic_settings import BaseSettings
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    database_url: Optional[str] = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "agent_poc_db"
    db_user: str = "username"
    db_password: str = "password"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env

    @property
    def get_database_url(self) -> str:
        """Get the complete database URL."""
        if self.database_url:
            return self.database_url

        return (
            f"postgresql://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )


# Database settings
db_settings = DatabaseSettings()

# Create database engine
engine = create_engine(
    db_settings.get_database_url,
    poolclass=StaticPool,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in db_settings.get_database_url else {}
    ),
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


class Conversation(Base):
    """Conversation model for storing conversation metadata."""

    __tablename__ = "conversations"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class ConversationMessage(Base):
    """Conversation message model for storing individual messages."""

    __tablename__ = "conversation_messages"

    id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, nullable=False, index=True)
    message_type = Column(String, nullable=False)  # 'human', 'ai', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    message_metadata = Column(Text)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
