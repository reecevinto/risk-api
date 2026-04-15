from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.api_key import APIKey
from app.core.security import generate_api_key, get_current_user

router = APIRouter()


# 🔹 Test route
@router.get("/test")
def test_auth():
    return {"message": "Auth route working"}


# ============================================================
# 🔥 Generate API Key
# ============================================================
@router.post("/generate-key/{user_id}")
def generate_api_key_route(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    api_key_value = generate_api_key()

    api_key = APIKey(
        key=api_key_value,
        user_id=user.id
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "api_key": api_key_value,
        "user_id": user.id,
        "message": "Store this key securely"
    }


# ============================================================
# 🔐 Protected endpoint (CLEAN + REUSABLE)
# ============================================================
@router.get("/protected")
def protected_route(
    user: User = Depends(get_current_user)
):
    return {
        "message": "Access granted",
        "user": {
            "id": user.id,
            "email": user.email
        }
    }