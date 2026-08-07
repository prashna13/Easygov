"""
schemas.py
----------
Pydantic schemas for request and response validation in EasyGov FastAPI backend.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime


# ── AUTH SCHEMAS ──────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    citizenship_number: Optional[str] = None
    province: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str] = None
    citizenship_number: Optional[str] = None
    province: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── DASHBOARD SCHEMAS ─────────────────────────────────────────────────────────

class GovServiceOut(BaseModel):
    id: int
    title: str
    category: str
    description: Optional[str] = None
    department: Optional[str] = None
    estimated_days: Optional[int] = None
    fee_npr: int = 0
    is_recommended: Optional[bool] = False

    class Config:
        from_attributes = True


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryOut(BaseModel):
    user_id: int
    messages: List[ChatMessageOut]

    class Config:
        from_attributes = True


class DashboardOut(BaseModel):
    user_name: str
    services: List[GovServiceOut]
    recommendations: List[GovServiceOut]
