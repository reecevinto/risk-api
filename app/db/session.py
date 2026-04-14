from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL

# 🔥 Important: helps avoid connection issues in Docker + concurrency
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # checks broken connections automatically
    pool_recycle=300      # prevents stale DB connections
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Dependency used in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()