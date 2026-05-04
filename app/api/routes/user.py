from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.routes.auth import get_current_user
from app.models.api_key import APIKey

router = APIRouter()

@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    # 🔥 get latest API key for this user
    api_key = db.query(APIKey)\
        .filter(APIKey.user_id == user.id)\
        .order_by(APIKey.id.desc())\
        .first()

    return {
        "id": user.id,
        "email": user.email,
        "api_key": api_key.key if api_key else None
    }