from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.api_key import APIKey
from app.core.security import generate_api_key

router = APIRouter()


# 🔹 Test route
@router.get("/test")
def test_auth():
    return {"message": "Auth route working"}


# ============================================================
# 🔥 Generate API Key (FIXED ROUTE)
# ============================================================
@router.post("/generate-key/{user_id}")
def generate_api_key_route(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

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
        "message": "Store this key securely, it will not be shown again"
    }


# ============================================================
# 🔐 Protected endpoint (FIXED VERSION)
# ============================================================
@router.get("/protected")
def protected_route(
    x_api_key: str = Header(...),
    db: Session = Depends(get_db)
):
    # Validate API key
    key_record = db.query(APIKey).filter(
        APIKey.key == x_api_key
    ).first()

    if not key_record:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Get user linked to API key
    user = db.query(User).filter(User.id == key_record.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "message": "Access granted",
        "user": {
            "id": user.id,
            "email": user.email
        }
    }