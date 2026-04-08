from fastapi import FastAPI
from app.api.routes import risk, auth

app = FastAPI(title="Risk Intelligence API")

# Include routers
app.include_router(risk.router, prefix="/risk", tags=["Risk"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])


@app.get("/health")
def health_check():
    return {"status": "ok"}