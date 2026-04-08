from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
def test_risk():
    return {"message": "Risk route working"}