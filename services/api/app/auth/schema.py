"""Pydantic schemas for authentication."""
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserSchema(BaseModel):
    """User response schema."""
    id: str
    email: str
    name: Optional[str] = None
    picture_url: Optional[str] = None
    is_demo: bool = False

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """Session response schema."""
    ok: bool = True
    user: Optional[UserSchema] = None
