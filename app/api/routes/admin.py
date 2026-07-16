# app/api/routes/admin.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
#from app.models.request_log import RequestLog
from app.api.routes.auth import get_current_user
#from sqlalchemy import func
from app.services.reconciliation_service import reconcile_usage
from app.services.analytics_service import get_usage_analytics

router = APIRouter()

@router.get("/usage")
def get_usage(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    return get_usage_analytics(
        db=db,
        user_id=user.id
    )
# ============================================================
# DAY 4 PHASE 2
# REDIS ↔ POSTGRES RECONCILIATION
# ============================================================

@router.post("/reconcile")
def reconcile_metering(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return reconcile_usage(
        db=db,
        user_id=user.id
    )