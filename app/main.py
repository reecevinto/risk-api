from fastapi import FastAPI
from app.api.routes import risk, auth

app = FastAPI(title="Risk Intelligence API")


# 🔹 Public routes
app.include_router(auth.router, prefix="/auth", tags=["Auth"])


# 🔥 Risk routes (will be protected using API key dependency inside endpoints)
app.include_router(risk.router, prefix="/risk", tags=["Risk"])


# 🔹 Health check (public)
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "running"}