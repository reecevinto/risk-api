from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
import stripe
import os
from datetime import datetime

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

router = APIRouter()

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

stripe.api_key = STRIPE_SECRET


# ============================================================
# SAFE HELPERS (NEW - NON-BREAKING)
# ============================================================
def safe_get(obj, key, default=None):
    """
    Stripe objects can behave inconsistently.
    This prevents AttributeError crashes.
    """
    try:
        return getattr(obj, key, default)
    except Exception:
        return default


def sync_user_plan(db: Session, user: User):
    """
    Single source of truth rule:
    subscription drives user plan
    """

    latest_sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.id.desc())
        .first()
    )

    if not latest_sub:
        user.plan_id = 1  # FREE
        return

    if latest_sub.status in [ACTIVE, TRIALING]:
        user.plan_id = 2  # PRO
    else:
        user.plan_id = 1  # FREE downgrade


# ============================================================
# MAIN WEBHOOK
# ============================================================
@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    event_type = event["type"]
    data = event["data"]["object"]

    print(f"🔥 Stripe Event Received: {event_type}")

    # ============================================================
    # 1. CHECKOUT COMPLETED
    # ============================================================
    if event_type == "checkout.session.completed":

        customer_id = safe_get(data, "customer")

        user = db.query(User).filter(
            User.stripe_customer_id == customer_id
        ).first()

        if user:

            user.plan_id = 2  # temporary until subscription sync

            db.commit()

            print(f"✅ Checkout completed for {user.email}")


    # ============================================================
    # 2. SUBSCRIPTION CREATED
    # ============================================================
    elif event_type == "customer.subscription.created":

        customer_id = safe_get(data, "customer")
        sub_id = safe_get(data, "id")
        status = normalize_stripe_status(safe_get(data, "status"))
        period_end = safe_get(data, "current_period_end")

        user = db.query(User).filter(
            User.stripe_customer_id == customer_id
        ).first()

        if user and sub_id:

            existing = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == sub_id
            ).first()

            if not existing:

                sub = Subscription(
                    user_id=user.id,
                    stripe_subscription_id=sub_id,
                    status=status,
                    current_plan="PRO",
                    current_period_end=(
                        datetime.fromtimestamp(period_end)
                        if period_end
                        else None
                    )
                )

                db.add(sub)

                sync_user_plan(db, user)

                db.commit()

                print(f"✅ Subscription created: {sub_id}")


    # ============================================================
    # 3. SUBSCRIPTION UPDATED
    # ============================================================
    elif event_type == "customer.subscription.updated":

        sub_id = safe_get(data, "id")
        status = normalize_stripe_status(safe_get(data, "status"))
        period_end = safe_get(data, "current_period_end")

        sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == sub_id
        ).first()

        if sub:

            sub.status = status

            if period_end:
                sub.current_period_end = datetime.fromtimestamp(period_end)

            # SAFE USER RESOLVE (IMPORTANT FIX)
            user = db.query(User).filter(User.id == sub.user_id).first()
            if user:
                sync_user_plan(db, user)

            db.commit()

            print(f"🔁 Subscription updated: {sub_id}")


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

            print(f"❌ Subscription cancelled: {sub_id}")


    # ============================================================
    # 5. INVOICE PAID
    # ============================================================
    elif event_type == "invoice.paid":

        customer_id = safe_get(data, "customer")

        user = db.query(User).filter(
            User.stripe_customer_id == customer_id
        ).first()

        if user:

            sub = (
                db.query(Subscription)
                .filter(Subscription.user_id == user.id)
                .order_by(Subscription.id.desc())
                .first()
            )

            if sub:
                sub.status = ACTIVE

                sync_user_plan(db, user)

            db.commit()

            print(f"💰 Payment success for {customer_id}")


    # ============================================================
    # 6. PAYMENT FAILED
    # ============================================================
    elif event_type == "invoice.payment_failed":

        customer_id = safe_get(data, "customer")

        user = db.query(User).filter(
            User.stripe_customer_id == customer_id
        ).first()

        if user:

            sub = (
                db.query(Subscription)
                .filter(Subscription.user_id == user.id)
                .order_by(Subscription.id.desc())
                .first()
            )

            if sub:
                sub.status = PAST_DUE

                sync_user_plan(db, user)

            db.commit()

            print(f"⚠️ Payment failed for {customer_id}")

    return {"status": "success"}