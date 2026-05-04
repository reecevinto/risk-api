from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, phone, email, ip, risk
from app.api.routes import user, admin

app = FastAPI(title="Risk Intelligence API")

# 🔥 CORS (CRITICAL FOR DASHBOARD)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Auth
app.include_router(auth.router, prefix="/auth", tags=["Auth"])

# 🔹 Intelligence
app.include_router(phone.router, prefix="/phone", tags=["Phone"])
app.include_router(email.router, prefix="/email", tags=["Email"])
app.include_router(ip.router, prefix="/ip", tags=["IP"])

# 🔥 Risk
app.include_router(risk.router, prefix="/risk", tags=["Risk"])

# 🔥 DAY 11 ROUTES (IMPORTANT)
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

@app.get("/health")
def health_check():
    return {"status": "ok"}