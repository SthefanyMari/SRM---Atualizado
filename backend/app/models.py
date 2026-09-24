from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ContentDomainRecord(TimestampMixin, Base):
    __tablename__ = "content_domains"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    avatar: Mapped[str] = mapped_column(String(50), default="astronauta", nullable=False)

    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    preference: Mapped[UserPreference | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )
    interactions: Mapped[list[Interaction]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list[RecommendationFeedback]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def preference_profile(self) -> dict[str, Any]:
        return self.preference.profile if self.preference else {}


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="reset_tokens")


class Content(TimestampMixin, Base):
    __tablename__ = "contents"
    __table_args__ = (
        UniqueConstraint("source_name", "external_id", name="uq_content_source_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    external_url: Mapped[str | None] = mapped_column(String(1000))
    source_name: Mapped[str] = mapped_column(String(100), default="local", nullable=False)
    external_id: Mapped[str] = mapped_column(String(180), nullable=False)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    interactions: Mapped[list[Interaction]] = relationship(
        back_populates="content", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list[RecommendationFeedback]] = relationship(
        back_populates="content", cascade="all, delete-orphan"
    )


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="preference")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content_id: Mapped[int] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    interaction_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="interactions")
    content: Mapped[Content] = relationship(back_populates="interactions")


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content_id: Mapped[int] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    relevant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="feedbacks")
    content: Mapped[Content] = relationship(back_populates="feedbacks")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="chat_messages")
