from fastapi import APIRouter, Depends, HTTPException
from app.services.email_service import analyze_email
from app.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/analyze")
def analyze(email: str, user=Depends(get_current_user)):

    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    result = analyze_email(email)

    return {
        "input": email,
        "result": result,
        "user": {
            "id": user.id,
            "email": user.email
        }
    }