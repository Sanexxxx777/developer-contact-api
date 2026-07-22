from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class ContactCategory(str, Enum):
    project = "project"
    job = "job"
    consultation = "consultation"
    support = "support"
    other = "other"


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80, examples=["Alex Ivanov"])
    phone: str = Field(min_length=7, max_length=24, examples=["+7 999 123-45-67"])
    email: EmailStr = Field(examples=["alex@example.com"])
    comment: str = Field(
        min_length=10,
        max_length=3000,
        examples=["I would like to discuss a project."],
    )

    @field_validator("name", "comment")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = "".join(char for char in value if char.isdigit() or char == "+")
        digits = "".join(char for char in normalized if char.isdigit())
        if not 7 <= len(digits) <= 15 or normalized.count("+") > 1 or "+" in normalized[1:]:
            raise ValueError("phone must contain 7 to 15 digits and an optional leading +")
        return value.strip()


class AIAnalysis(BaseModel):
    sentiment: Sentiment
    category: ContactCategory
    priority: int = Field(ge=1, le=5)
    suggested_reply: str = Field(min_length=1, max_length=500)


class ContactResponse(BaseModel):
    id: str
    status: str
    message: str
    ai: AIAnalysis
    ai_fallback_used: bool
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    database: str


class MetricsResponse(BaseModel):
    total_contacts: int
    delivered_contacts: int
    failed_contacts: int
    ai_fallbacks: int
    by_category: dict[str, int]
