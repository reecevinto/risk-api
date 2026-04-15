from fastapi import APIRouter, Depends, HTTPException
from app.services.ip_service import analyze_ip
from app.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/analyze")
def analyze(ip: str, user=Depends(get_current_user)):

    if not ip:
        raise HTTPException(status_code=400, detail="IP required")

    result = analyze_ip(ip)

    return {
        "input": ip,
        "result": result,
        "user": {
            "id": user.id,
            "email": user.email
        }
    }