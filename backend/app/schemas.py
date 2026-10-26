from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class ContentDomain(str, Enum):
    MOVIE = "filme"
    MUSIC = "musica"
    BOOK = "livro"
    COURSE = "curso"
    PRODUCT = "produto"


class InteractionType(str, Enum):
    VIEW = "view"
    CLICK = "click"
    RATING = "rating"
    RECOMMENDATION = "recommendation"


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AdminUserCreate(UserCreate):
    role: UserRole = UserRole.USER


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    avatar: str = "astronauta"
    preference_profile: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserPublic
    message: str
    access_token: str | None = None


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordRecoveryResponse(BaseModel):
    message: str
    reset_token: str | None = None


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ContentBase(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=4)
    domain: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9_-]+$")
    category: str = Field(min_length=2, max_length=100)
    image_url: str | None = None
    external_url: str | None = None
    source_name: str = "local"
    external_id: str = Field(min_length=1, max_length=180)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_published: bool = True


class ContentCreate(ContentBase):
    pass


class ContentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    description: str | None = Field(default=None, min_length=4)
    domain: str | None = Field(default=None, min_length=2, max_length=40, pattern=r"^[a-z0-9_-]+$")
    category: str | None = Field(default=None, min_length=2, max_length=100)
    image_url: str | None = None
    external_url: str | None = None
    metadata: dict[str, Any] | None = None
    is_published: bool | None = None


class ContentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    title: str
    description: str
    domain: str
    category: str
    image_url: str | None
    external_url: str | None
    source_name: str
    external_id: str
    metadata: dict[str, Any] = Field(validation_alias="extra_data")
    is_published: bool
    created_at: datetime
    updated_at: datetime


class ContentList(BaseModel):
    total: int
    items: list[ContentPublic]


class InteractionCreate(BaseModel):
    content_id: int
    interaction_type: InteractionType
    value: float | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class InteractionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_id: int
    interaction_type: InteractionType
    value: float | None
    context: dict[str, Any]
    created_at: datetime
    content: ContentPublic | None = None


class PreferencePublic(BaseModel):
    preferred_domains: list[str] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)


class PreferencesUpdate(PreferencePublic):
    pass


class RecommendationItem(BaseModel):
    content: ContentPublic
    score: float
    reason: str

class RecommendationResponse(BaseModel):
    items: list[RecommendationItem]
    provider: str = "local"

class FeedbackCreate(BaseModel):
    content_id: int
    relevant: bool
    explanation: str | None = None


class AssistantRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1000)


class AssistantSource(BaseModel):
    content_id: int
    title: str
    domain: str


class AssistantResponse(BaseModel):
    answer: str
    sources: list[AssistantSource]
    provider: str = "local"


class ChatMessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar: str | None = Field(default=None, min_length=2, max_length=50)


class DomainCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)
    is_active: bool = True


class DomainUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class DomainPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None


class StatisticsResponse(BaseModel):
    users: int
    active_users: int
    contents: int
    interactions: int
    feedbacks: int
    contents_by_domain: dict[str, int]
    interactions_by_type: dict[str, int]
