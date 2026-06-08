from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    phone,
    email,
    ip,
    risk,
    user,
    admin,
    billing,
    webhooks
)

app = FastAPI(title="Africa Risk Intelligence API")


# ============================================================
# 🔥 CORS (CRITICAL FOR DASHBOARD + STRIPE)
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 🔐 AUTH ROUTES
# ============================================================
app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"]
)


# ============================================================
# 📡 INTELLIGENCE ROUTES
# ============================================================
app.include_router(
    phone.router,
    prefix="/phone",
    tags=["Phone"]
)

app.include_router(
    email.router,
    prefix="/email",
    tags=["Email"]
)

app.include_router(
    ip.router,
    prefix="/ip",
    tags=["IP"]
)


# ============================================================
# 🧠 RISK ENGINE
# ============================================================
app.include_router(
    risk.router,
    prefix="/risk",
    tags=["Risk"]
)


# ============================================================
# 👤 USER ROUTES
# ============================================================
app.include_router(
    user.router,
    prefix="/user",
    tags=["User"]
)


# ============================================================
# 📊 ADMIN / ANALYTICS
# ============================================================
app.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"]
)


# ============================================================
# 💳 BILLING ROUTES (DAY 14)
# ============================================================
app.include_router(
    billing.router,
    prefix="/billing",
    tags=["Billing"]
)


# ============================================================
# 🔔 STRIPE WEBHOOKS (DAY 14)
# ============================================================
app.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["Webhooks"]
)


# ============================================================
# ❤️ HEALTH CHECK
# ============================================================
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Africa Risk Intelligence API"
    }


# ============================================================
# 🏠 ROOT
# ============================================================
@app.get("/")
def root():
    return {
        "message": "Africa Risk Intelligence API running",
        "docs": "/docs",
        "health": "/health"
    }