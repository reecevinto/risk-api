from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import models so Alembic detects them
from app.models import user, api_key, request_log, risk_score