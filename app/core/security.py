import secrets
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.api_key import APIKey
from app.models.user import User


# ============================================================
# 🔑 API KEY GENERATOR (Day 3)
# ============================================================
def generate_api_key():
    return secrets.token_hex(32)


# ============================================================
# 🔐 AUTH DEPENDENCY (USED EVERYWHERE)
# ============================================================
def get_current_user(
    x_api_key: str = Header(...),
    db: Session = Depends(get_db)
):
    # 1. Find API key
    key_record = db.query(APIKey).filter(
        APIKey.key == x_api_key
    ).first()

    if not key_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    # 2. Find user
    user = db.query(User).filter(
        User.id == key_record.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user