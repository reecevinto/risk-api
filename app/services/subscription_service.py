from app.core.subscription_states import (
    ACTIVE,
    TRIALING,
    PAST_DUE,
    CANCELED
)


# ============================================================
# DAY 3 — STATE ENGINE HELPERS
# ============================================================

def is_subscription_active(subscription):
    """
    Active means user has full or trial access
    """

    if not subscription:
        return False

    return subscription.status in [
        ACTIVE,
        TRIALING
    ]


def is_subscription_blocked(subscription):
    """
    Blocked means user should NOT have access
    """

    if not subscription:
        return True

    return subscription.status in [
        PAST_DUE,
        CANCELED
    ]


# ============================================================
# DAY 3 ADDITION (IMPORTANT CONSISTENCY HELPER)
# ============================================================

def get_access_state(subscription):
    """
    Single unified decision function (VERY USEFUL for Day 3)
    """

    if not subscription:
        return "blocked"

    if subscription.status in [ACTIVE, TRIALING]:
        return "active"

    return "blocked"