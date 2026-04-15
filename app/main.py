from fastapi import FastAPI
from app.api.routes import risk, auth
from app.api.routes import risk, auth, phone
from app.api.routes import email
from app.api.routes import ip

app = FastAPI(title="Risk Intelligence API")

app.include_router(phone.router, prefix="/phone", tags=["Phone Intelligence"])
app.include_router(email.router, prefix="/email", tags=["Email Intelligence"])
app.include_router(ip.router, prefix="/ip", tags=["IP Intelligence"])




# 🔹 Public routes
app.include_router(auth.router, prefix="/auth", tags=["Auth"])


# 🔥 Risk routes (will be protected using API key dependency inside endpoints)
app.include_router(risk.router, prefix="/risk", tags=["Risk"])


# 🔹 Health check (public)
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "running"}