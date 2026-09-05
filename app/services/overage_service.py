"""
============================================================
DAY 6 — PHASE 2
OVERAGE CHARGING ENGINE

Purpose
-------
Responsible for handling API requests that exceed a user's
included monthly plan allowance.

This service DOES NOT execute SQL counting queries directly.

Usage counting belongs strictly to:

    app/services/metering_service.py

Responsibilities
----------------
✓ Detect overage status
✓ Calculate billable requests
✓ Calculate current overage charges
✓ Report metered usage events to Stripe
✓ Provide invoice estimations
============================================================
"""

import os
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import stripe

from app.models.user import User
from app.models.plan import Plan

from app.services.metering_service import (
    get_current_usage,
    get_plan_limit,
    overage_requests as get_overage_requests_count
)

logger = logging.getLogger(__name__)

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
    Returns True once the included quota has been reached or exceeded.

    Example:
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
    overage_count: int
) -> float:
    """
    Calculates the total overage cost based on the plan's overage price settings.

    Example:
        Price = $0.002 / request
        Requests = 500
        Total = $1.00
    """
    if not plan or not getattr(plan, "allow_overage", False):
        return 0.0

    price_per_req = float(getattr(plan, "overage_price", 0.0) or 0.0)
    return price_per_req * overage_count


# ============================================================
# MAIN OVERAGE CALCULATION
# ============================================================

def calculate_overage_charge(
    db: Session,
    user: User
) -> Dict[str, Any]:
    """
    Calculates the user's current overage metrics via PostgreSQL.

    Returns:
        {
            "is_overage": bool,
            "overage_requests": int,
            "price_per_request": float,
            "total_charge": float
        }

    This function serves as the single source of truth for all 
    overage pricing and request state evaluations.
    """
    plan = user.plan

    if plan is None:
        return {
            "is_overage": False,
            "overage_requests": 0,
            "price_per_request": 0.0,
            "total_charge": 0.0
        }

    # Fetch live PostgreSQL count and overage calculations
    overage_count = get_overage_requests_count(db, user)
    price_per_request = float(getattr(plan, "overage_price", 0.0) or 0.0)
    total_charge = calculate_overage_cost(plan, overage_count)

    return {
        "is_overage": overage_count > 0,
        "overage_requests": overage_count,
        "price_per_request": price_per_request,
        "total_charge": round(total_charge, 4)
    }


# ============================================================
# PROCESS A SINGLE REQUEST
# ============================================================

def process_overage(
    db: Session,
    user: User
) -> Dict[str, Any]:
    """
    Determines whether the CURRENT request is billable as an overage request.
    Useful for middleware, route logging, and request evaluation.
    """
    overage = calculate_overage_charge(db, user)

    return {
        "is_overage": overage["is_overage"],
        "charge": overage["price_per_request"]
    }


# ============================================================
# ESTIMATED MONTHLY INVOICE
# ============================================================

def estimate_invoice(
    db: Session,
    user: User
) -> Dict[str, Any]:
    """
    Returns the current month's estimated overage invoice breakdown.
    """
    overage = calculate_overage_charge(db, user)

    return {
        "overage_requests": overage["overage_requests"],
        "estimated_charge": overage["total_charge"]
    }


# ============================================================
# REPORT METERED USAGE TO STRIPE
# ============================================================

def report_overage_usage(
    stripe_customer_id: str,
    quantity: int = 1
) -> Optional[Any]:
    """
    Sends metered usage records to Stripe.

    Assumes the Stripe Product is configured with Metered Billing.
    Stripe automatically invoices customers at the end of the billing period.
    """
    if quantity <= 0 or not stripe_customer_id:
        return None

    try:
        return stripe.billing.MeterEvent.create(
            event_name="risk_api_overage",
            payload={
                "value": str(quantity),
                "stripe_customer_id": stripe_customer_id
            }
        )
    except Exception as e:
        logger.error(f"Failed to report metered overage event to Stripe: {str(e)}")
        return None