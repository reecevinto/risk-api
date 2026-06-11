from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
import stripe
import os
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.subscription import Subscription

router = APIRouter()

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

stripe.api_key = STRIPE_SECRET


# ============================================================
# MAIN STRIPE WEBHOOK ENTRYPOINT
# ============================================================
@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    event_type = event["type"]
    data = event["data"]["object"]

    print(f"🔥 Stripe Event Received: {event_type}")

    # ============================================================
    # 1. CHECKOUT COMPLETED
    # ============================================================
    if event_type == "checkout.session.completed":

        stripe_customer_id = getattr(
            data,
            "customer",
            None
        )

        user = db.query(User).filter(
            User.stripe_customer_id == stripe_customer_id
        ).first()

        if user:

            # PRO PLAN ID
            user.plan_id = 2

            db.commit()

            print(
                f"✅ Checkout completed for user {user.email}"
            )

    # ============================================================
    # 2. SUBSCRIPTION CREATED
    # ============================================================
    elif event_type == "customer.subscription.created":

        customer_id = getattr(
            data,
            "customer",
            None
        )

        sub_id = getattr(
            data,
            "id",
            None
        )

        status = getattr(
            data,
            "status",
            "active"
        )

        period_end = getattr(
            data,
            "current_period_end",
            None
        )

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
                db.commit()

                print(
                    f"✅ Subscription created: {sub_id}"
                )

    # ============================================================
    # 3. SUBSCRIPTION UPDATED
    # ============================================================
    elif event_type == "customer.subscription.updated":

        sub_id = getattr(
            data,
            "id",
            None
        )

        status = getattr(
            data,
            "status",
            None
        )

        period_end = getattr(
            data,
            "current_period_end",
            None
        )

        sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == sub_id
        ).first()

        if sub:

            sub.status = status

            sub.current_period_end = (
                datetime.fromtimestamp(period_end)
                if period_end
                else None
            )

            db.commit()

            print(
                f"✅ Subscription updated: {sub_id}"
            )

    # ============================================================
    # 4. SUBSCRIPTION DELETED
    # ============================================================
    elif event_type == "customer.subscription.deleted":

        sub_id = getattr(
            data,
            "id",
            None
        )

        sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == sub_id
        ).first()

        if sub:

            sub.status = "canceled"

            db.commit()

            print(
                f"❌ Subscription cancelled: {sub_id}"
            )

    # ============================================================
    # 5. INVOICE PAID
    # ============================================================
    elif event_type == "invoice.paid":

        customer_id = getattr(
            data,
            "customer",
            None
        )

        print(
            f"💰 Invoice paid for customer {customer_id}"
        )

    # ============================================================
    # 6. PAYMENT FAILED
    # ============================================================
    elif event_type == "invoice.payment_failed":

        customer_id = getattr(
            data,
            "customer",
            None
        )

        print(
            f"⚠️ Payment failed for customer {customer_id}"
        )

    return {
        "status": "success"
    }