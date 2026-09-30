"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

StatusType = Literal["open", "in_progress", "resolved", "closed"]
PriorityType = Literal["low", "medium", "high", "urgent"]
CategoryType = Literal["billing", "technical", "account", "general"]


class TicketCreate(BaseModel):
    """Payload for the public ticket-submission endpoint (website form)."""

    title: str = Field(..., min_length=3, max_length=255)
    body: str = Field(..., min_length=5)
    customer_email: EmailStr
    customer_name: Optional[str] = Field(default=None, max_length=120)


class TicketUpdate(BaseModel):
    """Partial update from the agent dashboard."""

    status: Optional[StatusType] = None
    assignee: Optional[str] = Field(default=None, max_length=120)
    priority: Optional[PriorityType] = None
    category: Optional[CategoryType] = None
    suggested_reply: Optional[str] = None


class ReplySend(BaseModel):
    """Send a (possibly edited) reply to the customer and resolve the ticket."""

    reply: str = Field(..., min_length=2)


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    customer_email: str
    customer_name: Optional[str]
    status: str
    assignee: Optional[str]
    category: Optional[str]
    priority: Optional[str]
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    triage_source: Optional[str]
    suggested_reply: Optional[str]
    final_reply: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]


class StatsOut(BaseModel):
    total_tickets: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_category: dict[str, int]
    by_sentiment: dict[str, int]
    average_sentiment_score: Optional[float]
    resolution_rate: float
