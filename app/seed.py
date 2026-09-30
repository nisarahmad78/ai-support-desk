"""Seed the database with realistic sample tickets.

Usage:
    python -m app.seed           # add sample tickets (skips if not empty)
    python -m app.seed --force   # wipe and re-seed

Each sample ticket is run through the triage engine, exactly like a real
submission, so the dashboard shows meaningful data immediately.
"""
import sys

from .database import SessionLocal, init_db
from .models import Ticket
from .triage import run_triage

SAMPLE_TICKETS = [
    dict(
        customer_name="Sarah Mitchell",
        customer_email="sarah.mitchell@gmail.com",
        title="Charged twice for my subscription this month",
        body=(
            "Hi, I just checked my bank statement and I was charged twice for "
            "the Pro subscription this month - once on the 3rd and again on "
            "the 5th. This is really frustrating. Please refund the duplicate "
            "charge as soon as possible."
        ),
        status="open",
        assignee=None,
    ),
    dict(
        customer_name="David Okafor",
        customer_email="david.okafor@brightline.io",
        title="URGENT: Dashboard is down for our whole team",
        body=(
            "Our entire team of 25 people cannot access the dashboard since "
            "9am. We just get a blank screen after login. Production reporting "
            "is blocked and our clients are complaining. This is critical, "
            "please treat as urgent."
        ),
        status="in_progress",
        assignee="Agent Priya",
    ),
    dict(
        customer_name="Emily Chen",
        customer_email="emily.chen@outlook.com",
        title="How do I export my reports to CSV?",
        body=(
            "Hello, I love the reporting feature so far. I could not find a "
            "way to export a report to CSV though - is that possible? Thanks "
            "in advance for your help!"
        ),
        status="open",
        assignee=None,
    ),
    dict(
        customer_name="Marcus Webb",
        customer_email="mwebb@webbstudios.com",
        title="Password reset email never arrives",
        body=(
            "I have tried resetting my password four times in the last hour "
            "and the reset email never arrives. I checked spam as well. I am "
            "locked out of my account and have a deadline today. Please help."
        ),
        status="open",
        assignee=None,
    ),
    dict(
        customer_name="Aisha Rahman",
        customer_email="aisha.rahman@novaretail.com",
        title="Invoice shows the wrong VAT amount",
        body=(
            "Our latest invoice (#INV-2481) shows VAT calculated at 20% but "
            "our account is registered in a 5% VAT region. Could you correct "
            "the invoice and reissue it before our finance team closes the "
            "month?"
        ),
        status="open",
        assignee="Agent Tom",
    ),
    dict(
        customer_name="Liam Donovan",
        customer_email="liam.donovan@gmail.com",
        title="App crashes every time I upload a file over 10MB",
        body=(
            "Every time I try to upload a file larger than about 10MB the "
            "app crashes with a generic error. Smaller files work fine. I "
            "tried Chrome and Firefox, same result. This is blocking my "
            "client deliverables."
        ),
        status="in_progress",
        assignee="Agent Priya",
    ),
    dict(
        customer_name="Sofia Rossi",
        customer_email="sofia.rossi@rossidesign.it",
        title="Can I change the email address on my account?",
        body=(
            "Hi team, I got married and would like to change the email "
            "address linked to my account to my new one. I could not find "
            "the option in account settings. Thanks!"
        ),
        status="resolved",
        assignee="Agent Tom",
    ),
    dict(
        customer_name="James Park",
        customer_email="james.park@techflow.co",
        title="API returns 500 errors since yesterday's deploy",
        body=(
            "Since yesterday evening our integration gets intermittent 500 "
            "errors from the /v1/reports endpoint, roughly one in five "
            "requests. Nothing changed on our side. Is there a known issue? "
            "Our sync jobs keep failing."
        ),
        status="open",
        assignee=None,
    ),
    dict(
        customer_name="Fatima Noor",
        customer_email="fatima.noor@eduplus.org",
        title="Coupon code not applying at checkout",
        body=(
            "I received a 20% discount coupon for the annual plan but at "
            "checkout it says the coupon is invalid. The code is WELCOME20 "
            "and it should be valid until the end of the month. Can you "
            "check?"
        ),
        status="open",
        assignee=None,
    ),
    dict(
        customer_name="Tom Becker",
        customer_email="tom.becker@beckerlogistics.de",
        title="Absolutely terrible experience - cancelling everything",
        body=(
            "This is the third time I am writing about the same sync "
            "problem and nobody has fixed it. The service is useless to us "
            "like this. I want a full refund for the last two months and I "
            "am cancelling our subscription. Completely unacceptable."
        ),
        status="in_progress",
        assignee="Agent Priya",
    ),
    dict(
        customer_name="Grace Liu",
        customer_email="grace.liu@liufinance.com",
        title="Thank you - and one small feature question",
        body=(
            "Just wanted to say thank you, the new analytics view is "
            "excellent and saved our team hours this week. One question: do "
            "you plan to add scheduled email reports? That would be perfect "
            "for our Monday meetings."
        ),
        status="resolved",
        assignee="Agent Tom",
    ),
    dict(
        customer_name="Omar Haddad",
        customer_email="omar.haddad@haddadtrading.com",
        title="Two-factor authentication codes stopped working",
        body=(
            "Since this morning my authenticator codes are being rejected "
            "even though the time on my phone is correct. I can log in with "
            "my password but 2FA always fails. Please help me regain secure "
            "access."
        ),
        status="open",
        assignee=None,
    ),
    dict(
        customer_name="Nina Petrova",
        customer_email="nina.petrova@petrovaconsulting.com",
        title="Upgrade to annual plan - how is the price calculated?",
        body=(
            "We are on the monthly Pro plan and want to switch to annual "
            "billing. Will the amount we already paid this month be credited "
            "against the annual price? A short breakdown would be great."
        ),
        status="open",
        assignee=None,
    ),
    dict(
        customer_name="Chris Evans",
        customer_email="chris.evans@evansmedia.net",
        title="Data export stuck at 99% for two days",
        body=(
            "I started a full data export on Monday and it is still stuck "
            "at 99%. I need this export for a compliance audit next week, so "
            "it is becoming urgent. Can someone look into it please?"
        ),
        status="in_progress",
        assignee="Agent Priya",
    ),
    dict(
        customer_name="Hannah Kim",
        customer_email="hannah.kim@kimandco.kr",
        title="Delete my account and personal data",
        body=(
            "Hi, I no longer use the service and would like my account and "
            "all personal data deleted, as per your privacy policy. Please "
            "confirm once it is done."
        ),
        status="open",
        assignee=None,
    ),
]


def seed(force: bool = False) -> int:
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(Ticket).count()
        if existing and not force:
            print(f"Database already has {existing} tickets - skipping "
                  f"(use --force to re-seed).")
            return existing
        if force:
            db.query(Ticket).delete()
            db.commit()

        for sample in SAMPLE_TICKETS:
            result = run_triage(
                title=sample["title"],
                body=sample["body"],
                customer_email=sample["customer_email"],
                customer_name=sample["customer_name"],
            )
            ticket = Ticket(
                title=sample["title"],
                body=sample["body"],
                customer_email=sample["customer_email"],
                customer_name=sample["customer_name"],
                status=sample["status"],
                assignee=sample["assignee"],
                category=result.category,
                priority=result.priority,
                sentiment=result.sentiment,
                sentiment_score=result.sentiment_score,
                suggested_reply=result.suggested_reply,
                triage_source=result.source,
            )
            db.add(ticket)
        db.commit()
        count = db.query(Ticket).count()
        print(f"Seeded {count} tickets.")
        return count
    finally:
        db.close()


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
