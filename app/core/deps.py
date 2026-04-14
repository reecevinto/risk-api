from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.api_key import APIKey

def get_current_user(
    x_api_key: str = Header(None),
    db: Session = Depends(get_db)
):
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key missing"
        )

    key = db.query(APIKey).filter(APIKey.key == x_api_key).first()

    if not key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    return key.user