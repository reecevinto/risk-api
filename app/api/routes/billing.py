from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os

from app.db.session import get_db
from app.api.routes.auth import get_current_user
from app.services.billing_service import create_checkout_session

router = APIRouter()


# ============================================================
# PRO CHECKOUT
# ============================================================
@router.post("/checkout/pro")
def checkout_pro(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    url = create_checkout_session(
        user,
        os.getenv("PRO_PRICE_ID")
    )

    return {"checkout_url": url}


# ============================================================
# ENTERPRISE CHECKOUT
# ============================================================
@router.post("/checkout/enterprise")
def checkout_enterprise(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    url = create_checkout_session(
        user,
        os.getenv("ENTERPRISE_PRICE_ID")
    )

    return {"checkout_url": url}