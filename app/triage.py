"""AI triage engine.

Two modes:

1. Rule-based mode (default, no API keys required):
   keyword scoring classifies the ticket into a category, urgency signals
   plus sentiment set the priority, a small lexicon scores sentiment, and
   a reply is drafted from category templates.

2. LLM mode (optional): when OPENAI_API_KEY is configured, an
   OpenAI-compatible chat model performs the same classification and
   drafts the reply. Any failure falls back to the rule engine, so the
   app never hard-depends on an external service.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .config import settings
from .reply_templates import EMPATHY_OPENER, TEMPLATES

# ---------------------------------------------------------------------------
# Lexicons
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "billing": [
        "refund", "charge", "charged", "charging", "invoice", "payment",
        "billing", "bill", "subscription", "price", "pricing", "discount",
        "coupon", "credit card", "debit card", "declined", "overcharged",
        "receipt", "plan", "renewal", "renew", "money back", "vat", "tax",
    ],
    "technical": [
        "error", "bug", "crash", "crashes", "not working", "broken",
        "slow", "timeout", "times out", "500", "404", "fails", "failed",
        "failure", "freeze", "freezes", "glitch", "upload", "download",
        "export", "import", "sync", "api", "integration", "blank screen",
        "white screen", "won't load", "doesn't load", "stuck",
    ],
    "account": [
        "password", "login", "log in", "sign in", "sign-in", "locked",
        "two-factor", "2fa", "verification code", "change my email",
        "profile", "username", "access my account", "sign up", "register",
        "delete my account", "account settings",
    ],
}

URGENT_SIGNALS = [
    "urgent", "asap", "immediately", "emergency", "critical",
    "production is down", "site is down", "service is down", "outage",
    "data loss", "lost all", "security breach", "breach", "hacked",
    "charged twice", "double charged", "locked out", "cannot access",
    "can't access", "cant access", "legal", "lawyer", "deadline today",
]

HIGH_SIGNALS = [
    "error", "crash", "not working", "broken", "refund", "fails",
    "failed", "angry", "frustrated", "unacceptable", "worst",
    "blocked", "blocking", "losing money", "customers complaining",
]

POSITIVE_WORDS = [
    "thanks", "thank you", "great", "excellent", "amazing", "awesome",
    "love", "happy", "pleased", "perfect", "wonderful", "helpful",
    "appreciate", "impressed", "fantastic", "brilliant", "easy",
]

NEGATIVE_WORDS = [
    "angry", "frustrated", "frustrating", "terrible", "awful", "worst",
    "horrible", "disappointed", "disappointing", "useless", "pathetic",
    "unacceptable", "ridiculous", "hate", "annoying", "annoyed",
    "furious", "outrageous", "scam", "waste", "incompetent",
]


@dataclass
class TriageResult:
    category: str
    priority: str
    sentiment: str
    sentiment_score: float
    suggested_reply: str
    source: str  # "rules" | "llm"


# ---------------------------------------------------------------------------
# Rule-based engine
# ---------------------------------------------------------------------------

def _hits(text: str, phrases: list[str]) -> int:
    return sum(1 for p in phrases if p in text)


def classify_category(text: str) -> str:
    scores = {
        category: _hits(text, keywords)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def score_sentiment(text: str) -> tuple[str, float]:
    pos = _hits(text, POSITIVE_WORDS)
    neg = _hits(text, NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return "neutral", 0.0
    score = round((pos - neg) / total, 2)  # -1.0 .. 1.0
    if score > 0.15:
        return "positive", score
    if score < -0.15:
        return "negative", score
    return "neutral", score


def classify_priority(text: str, sentiment: str) -> str:
    score = 0
    score += 3 * _hits(text, URGENT_SIGNALS)
    score += 2 * _hits(text, HIGH_SIGNALS)
    if sentiment == "negative":
        score += 2
    if score >= 5:
        return "urgent"
    if score >= 2:
        return "high"
    if score >= 1 or sentiment == "negative":
        return "medium"
    return "low" if _hits(text, POSITIVE_WORDS) > 0 else "medium"


def _first_name(customer_name: str | None, email: str) -> str:
    if customer_name and customer_name.strip():
        return customer_name.strip().split()[0]
    local = email.split("@")[0]
    guess = re.split(r"[._\-0-9]+", local)[0]
    return guess.capitalize() if guess else "there"


def draft_reply(
    category: str, sentiment: str, title: str,
    customer_name: str | None, email: str,
) -> str:
    name = _first_name(customer_name, email)
    reference = title.strip().rstrip(".").lower()
    body = TEMPLATES[category].format(name=name, reference=reference)
    if sentiment == "negative":
        body = EMPATHY_OPENER + body
    return body


def triage_with_rules(
    title: str, body: str, customer_email: str,
    customer_name: str | None = None,
) -> TriageResult:
    text = f"{title}\n{body}".lower()
    category = classify_category(text)
    sentiment, sentiment_score = score_sentiment(text)
    priority = classify_priority(text, sentiment)
    reply = draft_reply(category, sentiment, title, customer_name, customer_email)
    return TriageResult(
        category=category,
        priority=priority,
        sentiment=sentiment,
        sentiment_score=sentiment_score,
        suggested_reply=reply,
        source="rules",
    )


# ---------------------------------------------------------------------------
# Optional LLM mode
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """You are the triage engine of a customer support desk.
Given a support ticket, respond with ONLY a JSON object with these keys:
- "category": one of "billing", "technical", "account", "general"
- "priority": one of "low", "medium", "high", "urgent"
- "sentiment": one of "positive", "neutral", "negative"
- "sentiment_score": number from -1.0 (very negative) to 1.0 (very positive)
- "suggested_reply": a polite, helpful first reply the agent can send,
  addressing the customer by first name, 80-140 words, signed "Support Team".
No markdown, no extra text, JSON only."""


def triage_with_llm(
    title: str, body: str, customer_email: str,
    customer_name: str | None = None,
) -> TriageResult:
    from openai import OpenAI  # imported lazily; only needed in LLM mode

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    user_prompt = (
        f"Customer name: {customer_name or 'unknown'}\n"
        f"Customer email: {customer_email}\n"
        f"Subject: {title}\n\nMessage:\n{body}"
    )
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)

    valid_categories = {"billing", "technical", "account", "general"}
    valid_priorities = {"low", "medium", "high", "urgent"}
    valid_sentiments = {"positive", "neutral", "negative"}
    if (
        data.get("category") not in valid_categories
        or data.get("priority") not in valid_priorities
        or data.get("sentiment") not in valid_sentiments
        or not data.get("suggested_reply")
    ):
        raise ValueError("LLM returned an invalid triage payload")

    return TriageResult(
        category=data["category"],
        priority=data["priority"],
        sentiment=data["sentiment"],
        sentiment_score=float(data.get("sentiment_score", 0.0)),
        suggested_reply=str(data["suggested_reply"]),
        source="llm",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_triage(
    title: str, body: str, customer_email: str,
    customer_name: str | None = None,
) -> TriageResult:
    """Triage one ticket, preferring the LLM when configured."""
    if settings.llm_enabled:
        try:
            return triage_with_llm(title, body, customer_email, customer_name)
        except Exception:
            # Never let an LLM outage break ticket intake.
            pass
    return triage_with_rules(title, body, customer_email, customer_name)
