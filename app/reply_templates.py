"""Reply templates used by the triage engine to draft a first response.

Each template is written the way a good support agent would write: it
acknowledges the issue, states the next step, and gives a time frame.
``{name}`` is the customer's first name and ``{reference}`` a short
description of the issue derived from the ticket title.
"""

TEMPLATES: dict[str, str] = {
    "billing": (
        "Hi {name},\n\n"
        "Thanks for reaching out about this billing matter. I have reviewed "
        "your account and opened an internal check on \"{reference}\".\n\n"
        "If a charge turns out to be incorrect, we will refund it to your "
        "original payment method within 3-5 business days, and you will get "
        "a confirmation email as soon as it is processed.\n\n"
        "In the meantime, could you confirm the last four digits of the card "
        "that was charged? That helps us locate the transaction faster.\n\n"
        "Thanks for your patience,\nSupport Team"
    ),
    "technical": (
        "Hi {name},\n\n"
        "Sorry you are running into this problem. I have logged "
        "\"{reference}\" with our technical team and marked it for "
        "investigation.\n\n"
        "A few quick things that often help right away:\n"
        "1. Refresh the page or restart the app.\n"
        "2. Clear your browser cache, or try a private/incognito window.\n"
        "3. Check that you are on the latest version.\n\n"
        "If it still happens, please send us a screenshot of what you see "
        "and the exact time it occurred - that will help us reproduce it. "
        "We will update you within one business day.\n\n"
        "Thanks for flagging this,\nSupport Team"
    ),
    "account": (
        "Hi {name},\n\n"
        "Thanks for contacting us about your account. For \"{reference}\", "
        "the fastest fix is usually a fresh secure link from our side, which "
        "I have just sent to your email address.\n\n"
        "Please use that link within 30 minutes. If you did not request this "
        "change, let us know right away so we can secure your account.\n\n"
        "Still stuck after that? Reply to this message and we will walk "
        "through it together.\n\n"
        "Best regards,\nSupport Team"
    ),
    "general": (
        "Hi {name},\n\n"
        "Thanks for getting in touch about \"{reference}\". I have passed "
        "your message to the right person on our team, and we will get back "
        "to you with a full answer within one business day.\n\n"
        "If anything about your request is time-sensitive, just reply here "
        "and let us know - we will prioritize it.\n\n"
        "Thanks for writing in,\nSupport Team"
    ),
}

# Used when the sentiment is strongly negative: a short empathy opener is
# prepended to whichever template was selected.
EMPATHY_OPENER = (
    "First of all, I am really sorry for the frustration this has caused - "
    "that is not the experience we want you to have.\n\n"
)
