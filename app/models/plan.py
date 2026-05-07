from sqlalchemy import Column, Integer, String
from app.db.base import Base

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, unique=True)
    request_limit = Column(Integer)