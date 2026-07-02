"""
============================================================
DAY 6 — PHASE 2
OVERAGE CHARGING ENGINE

Purpose
-------
Responsible for handling API requests that exceed a user's
included monthly plan allowance.

This service DOES NOT count usage.

Usage counting belongs to:

    app/services/metering_service.py

Responsibilities
----------------

✓ Detect overage
✓ Calculate billable requests
✓ Calculate current overage charges
✓ Report metered usage to Stripe
✓ Provide invoice estimation

============================================================
"""

import os
import stripe

from app.models.user import User
from app.models.plan import Plan

from app.services.metering_service import (
    get_usage
)

# ============================================================
# STRIPE CONFIGURATION
# ============================================================

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# ============================================================
# CHECK WHETHER A REQUEST IS AN OVERAGE
# ============================================================

def is_overage_request(
    usage: int,
    limit: int
) -> bool:
    """
    Returns True once the included quota
    has been reached.

    Example

        Limit = 1000

        Usage = 1000

        Next request becomes overage.
    """

    return usage >= limit


# ============================================================
# CALCULATE OVERAGE COST
# ============================================================

def calculate_overage_cost(
    plan: Plan,
    overage_requests: int
) -> float:
    """
    Calculates the total overage cost.

    Example

        Price = $0.002/request

        Requests = 500

        Total = $1.00
    """

    if not plan.allow_overage:
        return 0.0

    return float(plan.overage_price) * overage_requests


# ============================================================
# MAIN OVERAGE CALCULATION
# ============================================================

def calculate_overage_charge(
    user: User
):
    """
    Calculates the user's current overage.

    Returns

    {
        overage_requests,
        price_per_request,
        total_charge,
        is_overage
    }

    This function is intended to be the
    single source of truth for all overage
    calculations.
    """

    plan = user.plan

    if plan is None:

        return {

            "is_overage": False,

            "overage_requests": 0,

            "price_per_request": 0.0,

            "total_charge": 0.0

        }

    usage = get_usage(user.id)

    limit = plan.request_limit

    overage_requests = max(
        usage - limit,
        0
    )

    total_charge = calculate_overage_cost(
        plan,
        overage_requests
    )

    return {

        "is_overage": overage_requests > 0,

        "overage_requests": overage_requests,

        "price_per_request": float(
            plan.overage_price
        ),

        "total_charge": round(
            total_charge,
            4
        )

    }


# ============================================================
# PROCESS A SINGLE REQUEST
# ============================================================

def process_overage(
    user: User
):
    """
    Determines whether the CURRENT request
    is billable as an overage request.

    This helper is useful inside API routes.
    """

    overage = calculate_overage_charge(user)

    return {

        "is_overage": overage["is_overage"],

        "charge": overage["price_per_request"]

    }


# ============================================================
# ESTIMATED MONTHLY INVOICE
# ============================================================

def estimate_invoice(
    user: User
):
    """
    Returns the current month's estimated
    overage invoice.

    Example

        Included:
            1000 requests

        Actual:
            1375 requests

        Overage:
            375 requests

        Price:
            $0.002/request

        Estimated:
            $0.75
    """

    overage = calculate_overage_charge(user)

    return {

        "overage_requests":
            overage["overage_requests"],

        "estimated_charge":
            overage["total_charge"]

    }


# ============================================================
# REPORT METERED USAGE TO STRIPE
# ============================================================

def report_overage_usage(
    subscription_item_id: str,
    quantity: int = 1
):
    """
    Sends usage records to Stripe.

    Assumes the Stripe Product has been
    configured as a Metered Billing product.

    Stripe automatically invoices customers
    at the end of the billing period.
    """

    if quantity <= 0:
        return None

    return stripe.billing.MeterEvent.create(

        event_name="risk_api_overage",

        payload={

            "value": str(quantity),

            "stripe_customer_id":
                subscription_item_id

        }

    )