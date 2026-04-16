from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class RiskRequest(BaseModel):
    email: Optional[EmailStr] = Field(
        default=None,
        example="test@gmail.com"
    )
    phone: Optional[str] = Field(
        default=None,
        example="+254712345678"
    )
    ip: Optional[str] = Field(
        default=None,
        example="8.8.8.8"
    )

    class Config:
        schema_extra = {
            "example": {
                "email": "test@gmail.com",
                "phone": "+254712345678",
                "ip": "8.8.8.8"
            }
        }