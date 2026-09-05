"""
============================================================
BILLING ROUTES

Purpose
-------
Exposes API endpoints for initiating Stripe checkout sessions
for Pro and Enterprise subscription tiers.
============================================================
"""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.routes.auth import get_current_user
from app.models.user import User
from app.services.billing_service import create_checkout_session

logger = logging.getLogger(__name__)

router = APIRouter()

# Evaluate price IDs at module load for fast runtime availability
PRO_PRICE_ID = os.getenv("PRO_PRICE_ID")
ENTERPRISE_PRICE_ID = os.getenv("ENTERPRISE_PRICE_ID")


# ============================================================
# HELPER FUNCTION
# ============================================================

def _handle_checkout(
    db: Session,
    user: User,
    price_id: str | None,
    tier_name: str
) -> dict[str, str]:
    """
    Internal helper to validate configuration, invoke the billing service,
    log successful transactions, and handle errors uniformly.
    """
    if not price_id:
        logger.error(f"{tier_name.upper()}_PRICE_ID environment variable is missing.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{tier_name.title()} tier pricing configuration is unavailable."
        )

    try:
        url = create_checkout_session(
            db=db,
            user=user,
            price_id=price_id
        )
        logger.info(
            "Successfully created %s checkout session for User ID %s (%s)",
            tier_name.title(),
            user.id,
            user.email
        )
        return {"checkout_url": url}
    except Exception:
        logger.exception(
            "Failed to initiate %s checkout session for User ID %s",
            tier_name.lower(),
            user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create checkout session. Please try again later."
        )


# ============================================================
# PRO CHECKOUT
# ============================================================

@router.post("/checkout/pro")
def checkout_pro(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> dict[str, str]:
    """
    Initiates a Stripe Checkout Session for the Pro tier.
    """
    return _handle_checkout(
        db=db,
        user=user,
        price_id=PRO_PRICE_ID,
        tier_name="pro"
    )


# ============================================================
# ENTERPRISE CHECKOUT
# ============================================================

@router.post("/checkout/enterprise")
def checkout_enterprise(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> dict[str, str]:
    """
    Initiates a Stripe Checkout Session for the Enterprise tier.
    """
    return _handle_checkout(
        db=db,
        user=user,
        price_id=ENTERPRISE_PRICE_ID,
        tier_name="enterprise"
    )