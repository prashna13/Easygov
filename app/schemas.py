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
    age: Optional[int] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    onboarding_completed: bool = False
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── ONBOARDING SCHEMAS ───────────────────────────────────────────────────────

class OnboardingRequest(BaseModel):
    """First-login onboarding: age + which government documents are already completed.

    `completed_documents` is a list of document keys, e.g.:
      ["birth_certificate", "citizenship"]
    """
    age: int
    completed_documents: List[str] = []


class OnboardingResponse(BaseModel):
    onboarding_completed: bool
    recommended_next_step: Optional["GovServiceOut"] = None


# ── DASHBOARD SCHEMAS ─────────────────────────────────────────────────────────

class GovServiceOut(BaseModel):
    id: int
    title: str
    category: str
    description: Optional[str] = None
    guidance: Optional[str] = None
    department: Optional[str] = None
    estimated_days: Optional[int] = None
    fee_npr: int = 0
    is_recommended: Optional[bool] = False
    prerequisites_met: Optional[bool] = True
    missing_prerequisites: Optional[List[str]] = []

    class Config:
        from_attributes = True


class ServiceDetailOut(BaseModel):
    """Full detail for a single service, including prerequisite status."""
    service: GovServiceOut
    prerequisites_met: bool
    missing_prerequisites: List[str] = []
    recommended_next_step: Optional[GovServiceOut] = None
    application: Optional["ApplicationOut"] = None


# ── APPLICATION PROGRESS SCHEMAS ──────────────────────────────────────────────

class ProgressStepOut(BaseModel):
    """A single step within a user's application for a service."""
    step_number: int
    step_name: str
    step_description: Optional[str] = None
    status: str
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApplicationOut(BaseModel):
    """A user's application for a service, with step-level progress."""
    application_id: int
    service_id: int
    service_title: str
    status: str
    progress_percent: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    steps: List[ProgressStepOut] = []


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
    needs_onboarding: bool = False
    recommended_next_step: Optional[GovServiceOut] = None
