"""Database models."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Customer-submitted fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Workflow fields
    status: Mapped[str] = mapped_column(
        String(20), default="open", index=True
    )  # open | in_progress | resolved | closed
    assignee: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # AI triage fields (populated by the triage engine)
    category: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )  # billing | technical | account | general
    priority: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )  # low | medium | high | urgent
    sentiment: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # positive | neutral | negative
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    triage_source: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # rules | llm

    # Agent reply handling
    suggested_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_reply: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
