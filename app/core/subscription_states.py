# ============================
# DAY 3 — SUBSCRIPTION STATE ENGINE
# ============================

ACTIVE = "active"
TRIALING = "trialing"
CANCELED = "canceled"
PAST_DUE = "past_due"


def normalize_stripe_status(status: str) -> str:
    """
    Converts Stripe status → internal canonical state
    """

    if not status:
        return TRIALING  # safer default than ACTIVE for billing systems

    mapping = {
        "active": ACTIVE,
        "trialing": TRIALING,
        "canceled": CANCELED,
        "incomplete_expired": CANCELED,
        "unpaid": PAST_DUE,
        "past_due": PAST_DUE,
        "incomplete": TRIALING,  # FIX: incomplete should not be treated as PAST_DUE immediately
        "paused": PAST_DUE,      # SAFE ADD (Stripe edge case support)
    }

    return mapping.get(status, TRIALING)