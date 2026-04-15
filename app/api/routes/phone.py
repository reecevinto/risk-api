from fastapi import APIRouter, Depends, HTTPException

from app.services.phone_service import analyze_phone
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


# ============================================================
# 📱 PHONE INTELLIGENCE (DAY 4)
# ============================================================
@router.get("/analyze")
def analyze(
    phone: str,
    user: User = Depends(get_current_user)
):

    if not phone:
        raise HTTPException(
            status_code=400,
            detail="Phone number required"
        )

    result = analyze_phone(phone)

    return {
        "input": phone,
        "result": result,
        "user": {
            "id": user.id,
            "email": user.email
        }
    }