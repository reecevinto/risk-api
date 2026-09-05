"""
============================================================
STRIPE WEBHOOKS ROUTE

Purpose
-------
Listens for asynchronous event notifications from Stripe to update
user subscription states, billing period boundaries, and plan access.
============================================================
"""

import os
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
import stripe

from app.db.session import get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.core.subscription_states import (
    ACTIVE,
    TRIALING,
    PAST_DUE,
    CANCELED,
    normalize_stripe_status
)

logger = logging.getLogger(__name__)

router = APIRouter()

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

stripe.api_key = STRIPE_SECRET

# Module-level Plan Identifier Constants
PLAN_FREE_ID = 1
PLAN_PRO_ID = 2


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """
    Safely retrieves attributes or dict keys from Stripe API objects
    without raising AttributeErrors or KeyErrors.
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        return getattr(obj, key, default)
    except Exception:
        return default


def parse_timestamp(ts: Optional[int]) -> Optional[datetime]:
    """
    Converts a Unix timestamp integer from Stripe to a timezone-aware UTC datetime object.
    """
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception as e:
        logger.warning("Failed to parse timestamp '%s': %s", ts, e)
        return None


def sync_user_plan(db: Session, user: User) -> None:
    """
    Enforces the single-source-of-truth principle:
    The user's active subscription status directly drives their assigned plan ID.
    Determined chronologically by the latest subscription period end date.
    """
    latest_sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.current_period_end.desc().nullslast(), Subscription.id.desc())
        .first()
    )

    if not latest_sub:
        user.plan_id = PLAN_FREE_ID
        return

    if latest_sub.status in [ACTIVE, TRIALING]:
        user.plan_id = PLAN_PRO_ID
    else:
        user.plan_id = PLAN_FREE_ID  # Downgrade on unpaid/canceled states


# ============================================================
# MAIN WEBHOOK ROUTE
# ============================================================

@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receives and processes incoming Stripe webhook events.
    """
    if not WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET is not configured on the server.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook signing secret unconfigured."
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        logger.warning("Webhook request missing 'stripe-signature' header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header."
        )

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature."
        )
    except Exception as e:
        logger.exception("Error constructing Stripe webhook event.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook Error: {str(e)}"
        )

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("Stripe Webhook received: %s", event_type)

    try:
        # ============================================================
        # 1. CHECKOUT SESSION COMPLETED
        # ============================================================
        if event_type == "checkout.session.completed":
            customer_id = safe_get(data, "customer")
            client_ref_id = safe_get(data, "client_reference_id")

            user = None
            if customer_id:
                user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if not user and client_ref_id:
                try:
                    user = db.query(User).filter(User.id == int(client_ref_id)).first()
                except (ValueError, TypeError):
                    logger.warning("Invalid client_reference_id format: %s", client_ref_id)

            if user:
                if customer_id and not user.stripe_customer_id:
                    user.stripe_customer_id = customer_id
                    db.commit()
                logger.info("Checkout session validated for User ID %s (%s)", user.id, user.email)
            else:
                logger.warning("Checkout session completed but user could not be resolved. Customer ID: %s", customer_id)

        # ============================================================
        # 2. SUBSCRIPTION CREATED
        # ============================================================
        elif event_type == "customer.subscription.created":
            customer_id = safe_get(data, "customer")
            sub_id = safe_get(data, "id")
            raw_status = safe_get(data, "status")
            status_normalized = normalize_stripe_status(raw_status)
            
            period_start = parse_timestamp(safe_get(data, "current_period_start"))
            period_end = parse_timestamp(safe_get(data, "current_period_end"))

            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

            if user and sub_id:
                sub = db.query(Subscription).filter(
                    Subscription.stripe_subscription_id == sub_id
                ).first()

                if not sub:
                    sub = Subscription(
                        user_id=user.id,
                        stripe_subscription_id=sub_id,
                        status=status_normalized,
                        current_period_start=period_start,
                        current_period_end=period_end
                    )
                    db.add(sub)
                else:
                    sub.status = status_normalized
                    sub.current_period_start = period_start
                    sub.current_period_end = period_end

                sync_user_plan(db, user)
                db.commit()
                logger.info("Subscription created/synced: %s for User ID %s", sub_id, user.id)

        # ============================================================
        # 3. SUBSCRIPTION UPDATED
        # ============================================================
        elif event_type == "customer.subscription.updated":
            sub_id = safe_get(data, "id")
            raw_status = safe_get(data, "status")
            status_normalized = normalize_stripe_status(raw_status)
            
            period_start = parse_timestamp(safe_get(data, "current_period_start"))
            period_end = parse_timestamp(safe_get(data, "current_period_end"))

            sub = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == sub_id
            ).first()

            if sub:
                sub.status = status_normalized
                if period_start:
                    sub.current_period_start = period_start
                if period_end:
                    sub.current_period_end = period_end

                user = db.query(User).filter(User.id == sub.user_id).first()
                if user:
                    sync_user_plan(db, user)

                db.commit()
                logger.info("Subscription updated: %s for User ID %s", sub_id, sub.user_id)

        # ============================================================
        # 4. SUBSCRIPTION DELETED
        # ============================================================
        elif event_type == "customer.subscription.deleted":
            sub_id = safe_get(data, "id")

            sub = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == sub_id
            ).first()

            if sub:
                sub.status = CANCELED
                user = db.query(User).filter(User.id == sub.user_id).first()
                if user:
                    sync_user_plan(db, user)

                db.commit()
                logger.info("Subscription canceled: %s for User ID %s", sub_id, sub.user_id)

        # ============================================================
        # 5. INVOICE PAID
        # ============================================================
        elif event_type == "invoice.paid":
            customer_id = safe_get(data, "customer")
            sub_id = safe_get(data, "subscription")

            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

            if user:
                sub = None
                if sub_id:
                    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).first()
                if not sub:
                    sub = (
                        db.query(Subscription)
                        .filter(Subscription.user_id == user.id)
                        .order_by(Subscription.current_period_end.desc().nullslast(), Subscription.id.desc())
                        .first()
                    )

                if sub:
                    sub.status = ACTIVE
                    # Safely extract billing period boundaries across dict or object formats
                    lines = safe_get(data, "lines", {})
                    line_data = safe_get(lines, "data", [])
                    if line_data:
                        first_line = line_data[0]
                        period = safe_get(first_line, "period", {})
                        p_start = safe_get(period, "start")
                        p_end = safe_get(period, "end")

                        if p_start:
                            sub.current_period_start = parse_timestamp(p_start)
                        if p_end:
                            sub.current_period_end = parse_timestamp(p_end)

                    sync_user_plan(db, user)

                db.commit()
                logger.info("Invoice payment success processed for Customer ID %s", customer_id)

        # ============================================================
        # 6. INVOICE PAYMENT FAILED
        # ============================================================
        elif event_type == "invoice.payment_failed":
            customer_id = safe_get(data, "customer")

            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

            if user:
                sub = (
                    db.query(Subscription)
                    .filter(Subscription.user_id == user.id)
                    .order_by(Subscription.current_period_end.desc().nullslast(), Subscription.id.desc())
                    .first()
                )

                if sub:
                    sub.status = PAST_DUE
                    sync_user_plan(db, user)

                db.commit()
                logger.warning("Invoice payment failed for Customer ID %s", customer_id)

    except Exception:
        db.rollback()
        logger.exception("Failed processing webhook event: %s", event_type)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook event."
        )

    return {"status": "success"}