"""AI Support Desk API.

Ticket intake is decoupled from triage: creating a ticket returns
immediately and the AI triage runs as a background task. In this
single-process setup FastAPI's BackgroundTasks are enough; at scale the
same function moves to a task queue (Celery / RQ / arq) behind Redis
without changing the API. See README "Scaling notes".
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas, triage
from .database import SessionLocal, get_db, init_db

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="AI Support Desk",
    description="SaaS-style customer support with AI auto-triage.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# Background triage
# ---------------------------------------------------------------------------

def triage_ticket(ticket_id: int) -> None:
    """Run AI triage for one ticket and persist the results.

    Executed as a background task after ticket creation (and on demand via
    the retriage endpoint). Opens its own session because the request
    session is already closed by the time background tasks run.
    """
    db = SessionLocal()
    try:
        ticket = db.get(models.Ticket, ticket_id)
        if ticket is None:
            return
        result = triage.run_triage(
            title=ticket.title,
            body=ticket.body,
            customer_email=ticket.customer_email,
            customer_name=ticket.customer_name,
        )
        ticket.category = result.category
        ticket.priority = result.priority
        ticket.sentiment = result.sentiment
        ticket.sentiment_score = result.sentiment_score
        ticket.suggested_reply = result.suggested_reply
        ticket.triage_source = result.source
        if ticket.status == "open" and result.priority in ("high", "urgent"):
            ticket.status = "in_progress"
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Ticket endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/tickets", response_model=schemas.TicketOut, status_code=201)
def create_ticket(
    payload: schemas.TicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Public intake endpoint - this is what a website contact/help form
    would POST to. Returns instantly; triage fills in the AI fields a
    moment later."""
    ticket = models.Ticket(
        title=payload.title,
        body=payload.body,
        customer_email=payload.customer_email,
        customer_name=payload.customer_name,
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    background_tasks.add_task(triage_ticket, ticket.id)
    return ticket


@app.get("/api/tickets", response_model=list[schemas.TicketOut])
def list_tickets(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Ticket)
    if status:
        query = query.filter(models.Ticket.status == status)
    if priority:
        query = query.filter(models.Ticket.priority == priority)
    if category:
        query = query.filter(models.Ticket.category == category)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (models.Ticket.title.ilike(like))
            | (models.Ticket.body.ilike(like))
            | (models.Ticket.customer_email.ilike(like))
        )
    return (
        query.order_by(models.Ticket.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@app.get("/api/tickets/{ticket_id}", response_model=schemas.TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(models.Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.patch("/api/tickets/{ticket_id}", response_model=schemas.TicketOut)
def update_ticket(
    ticket_id: int,
    payload: schemas.TicketUpdate,
    db: Session = Depends(get_db),
):
    ticket = db.get(models.Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(ticket, field, value)
    if updates.get("status") == "resolved" and ticket.resolved_at is None:
        ticket.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.post("/api/tickets/{ticket_id}/reply", response_model=schemas.TicketOut)
def send_reply(
    ticket_id: int,
    payload: schemas.ReplySend,
    db: Session = Depends(get_db),
):
    """Accept the (possibly edited) reply, 'send' it to the customer and
    mark the ticket resolved. In production this is where the message
    would be handed to the mail provider / helpdesk integration."""
    ticket = db.get(models.Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.final_reply = payload.reply
    ticket.status = "resolved"
    ticket.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.post("/api/tickets/{ticket_id}/retriage", response_model=schemas.TicketOut)
def retriage_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Re-run AI triage for a ticket (synchronously, for the dashboard)."""
    if db.get(models.Ticket, ticket_id) is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    triage_ticket(ticket_id)
    db.expire_all()
    return db.get(models.Ticket, ticket_id)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@app.get("/api/stats", response_model=schemas.StatsOut)
def get_stats(db: Session = Depends(get_db)):
    def counts(column) -> dict[str, int]:
        rows = (
            db.query(column, func.count(models.Ticket.id))
            .group_by(column)
            .all()
        )
        return {str(key): count for key, count in rows if key is not None}

    total = db.query(func.count(models.Ticket.id)).scalar() or 0
    resolved = (
        db.query(func.count(models.Ticket.id))
        .filter(models.Ticket.status.in_(["resolved", "closed"]))
        .scalar()
        or 0
    )
    avg_sentiment = db.query(func.avg(models.Ticket.sentiment_score)).scalar()

    return schemas.StatsOut(
        total_tickets=total,
        by_status=counts(models.Ticket.status),
        by_priority=counts(models.Ticket.priority),
        by_category=counts(models.Ticket.category),
        by_sentiment=counts(models.Ticket.sentiment),
        average_sentiment_score=(
            round(float(avg_sentiment), 2) if avg_sentiment is not None else None
        ),
        resolution_rate=round(resolved / total, 2) if total else 0.0,
    )


# ---------------------------------------------------------------------------
# Frontend (single-page dashboard, served as static files)
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
