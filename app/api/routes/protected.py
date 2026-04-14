from fastapi import APIRouter, Depends
from app.core.deps import get_current_user

router = APIRouter()

@router.get("/protected")
def protected_route(current_user = Depends(get_current_user)):

    return {
        "message": "Access granted",
        "user_id": current_user.id,
        "email": current_user.email
    }