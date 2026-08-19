"""
models.py
---------
SQLAlchemy ORM models for EasyGov Nepal.

Tables:
  - users              : User accounts and profile data
  - gov_services       : Master catalog of all government services
  - prerequisite_rules : Defines which service must be done before another
  - user_services      : Tracks each user's engagement with each service
  - progress           : Step-level checklist within a user_service
  - documents          : User-uploaded files in their private document vault
  - government_offices : Static catalog of real Nepali government offices
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Float,
    ForeignKey, Text, UniqueConstraint, CheckConstraint, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


# ── ENUMS ─────────────────────────────────────────────────────────────────────

class ServiceStatus(str, enum.Enum):
    """Lifecycle status of a user's engagement with a government service."""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED   = "SUBMITTED"
    COMPLETED   = "COMPLETED"
    REJECTED    = "REJECTED"


class StepStatus(str, enum.Enum):
    """Lifecycle status of a single step within a user_service."""
    PENDING    = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED  = "COMPLETED"
    SKIPPED    = "SKIPPED"


# ── TABLE 1: users ─────────────────────────────────────────────────────────────

class User(Base):
    """
    Stores registered user accounts.

    Fields:
        id                  : Auto-increment primary key
        full_name           : Full legal name (as on citizenship)
        email               : Login identifier — must be unique
        phone               : Mobile number (Nepal format preferred, e.g. +977-98XXXXXXXX)
        password_hash       : bcrypt-hashed password (never plain-text)
        citizenship_number  : Nepal citizenship certificate number (unique, optional)
        date_of_birth       : Used for age verification (e.g. minor passport rules)
        address             : Current home address (ward/municipality)
        province            : One of Nepal's 7 provinces
        is_active           : Soft-delete flag (False = banned/deactivated)
        created_at          : Timestamp of registration
        updated_at          : Timestamp of last profile update
    """
    __tablename__ = "users"

    id                 = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name          = Column(String(200), nullable=False)
    email              = Column(String(255), unique=True, nullable=False, index=True)
    google_id          = Column(String(255), unique=True, nullable=True)
    phone              = Column(String(20), nullable=True)
    password_hash      = Column(String(255), nullable=False)
    citizenship_number = Column(String(50), unique=True, nullable=True)
    date_of_birth      = Column(Date, nullable=True)
    age                = Column(Integer, nullable=True)
    address            = Column(String(500), nullable=True)
    province           = Column(String(100), nullable=True)
    is_active          = Column(Boolean, default=True, nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    updated_at         = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    service_records = relationship("UserService", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship(
        "ChatMessage",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' name='{self.full_name}'>"


class ChatMessage(Base):
    """
    Stores chatbot conversation messages for a particular user.

    Fields:
        id         : Auto-increment primary key
        user_id    : FK to users.id
        role       : Who authored the message (user, assistant, system)
        content    : The text content of the message
        created_at : When this message was saved
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="chat_history")

    def __repr__(self):
        return f"<ChatMessage id={self.id} user={self.user_id} role='{self.role}'>"


# ── TABLE 2: gov_services ──────────────────────────────────────────────────────

class GovService(Base):
    """
    Master catalog of all government services offered through EasyGov.
    This replaces the hardcoded GOV_CATALOG list in main.py.

    Fields:
        id              : Auto-increment primary key
        title           : Short display name (e.g. "E-Passport Apply")
        title_ne        : Nepali display name (e.g. "विद्युतीय राहदानी")
        category        : Service category (e.g. "Identity", "Transport")
        category_ne     : Nepali service category
        description     : Human-readable explanation of the service
        description_ne  : Nepali explanation of the service
        guidance        : Full step-by-step guide (overview, prerequisites, documents,
                          procedure, fees, processing time, official resources)
        guidance_ne     : Nepali version of the full guide
        department      : Responsible government department/ministry
        estimated_days  : Average processing time in working days
        fee_npr         : Official government fee in Nepali Rupees (0 = free)
        is_active       : Flag to hide/show a service without deleting it
        created_at      : When this record was added to the catalog
    """
    __tablename__ = "gov_services"

    id             = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title          = Column(String(200), nullable=False)
    title_ne       = Column(String(200), nullable=True)
    category       = Column(String(100), nullable=False, index=True)
    category_ne    = Column(String(100), nullable=True)
    description    = Column(Text, nullable=True)
    description_ne = Column(Text, nullable=True)
    guidance       = Column(Text, nullable=True)
    guidance_ne    = Column(Text, nullable=True)
    department     = Column(String(200), nullable=True)
    estimated_days = Column(Integer, nullable=True)
    fee_npr        = Column(Integer, default=0, nullable=False)
    is_active      = Column(Boolean, default=True, nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user_records = relationship("UserService", back_populates="service")

    # A service may appear as either the dependent or the prerequisite in rules
    prerequisite_for = relationship(
        "PrerequisiteRule",
        foreign_keys="PrerequisiteRule.service_id",
        back_populates="service",
        cascade="all, delete-orphan"
    )
    is_prerequisite_of = relationship(
        "PrerequisiteRule",
        foreign_keys="PrerequisiteRule.prerequisite_service_id",
        back_populates="prerequisite_service"
    )

    def __repr__(self):
        return f"<GovService id={self.id} title='{self.title}' category='{self.category}'>"


# ── TABLE 3: prerequisite_rules ────────────────────────────────────────────────

class PrerequisiteRule(Base):
    """
    Defines a directed dependency between two government services.

    Example: To apply for an E-Passport, the user must first complete
    "Citizenship Certificate Copy" (is_mandatory=True).

    Fields:
        id                       : Auto-increment primary key
        service_id               : The service that HAS a prerequisite
        prerequisite_service_id  : The service that must be completed FIRST
        is_mandatory             : If True, the backend will block the dependent
                                   service until the prerequisite is COMPLETED.
                                   If False, it shows as a recommendation only.
        notes                    : Optional human-readable explanation of the rule
    """
    __tablename__ = "prerequisite_rules"

    id                      = Column(Integer, primary_key=True, index=True, autoincrement=True)
    service_id              = Column(Integer, ForeignKey("gov_services.id"), nullable=False)
    prerequisite_service_id = Column(Integer, ForeignKey("gov_services.id"), nullable=False)
    is_mandatory            = Column(Boolean, default=True, nullable=False)
    notes                   = Column(Text, nullable=True)

    # Prevent duplicate rules for the same pair
    __table_args__ = (
        UniqueConstraint("service_id", "prerequisite_service_id", name="uq_prerequisite_pair"),
    )

    # Relationships
    service              = relationship("GovService", foreign_keys=[service_id], back_populates="prerequisite_for")
    prerequisite_service = relationship("GovService", foreign_keys=[prerequisite_service_id], back_populates="is_prerequisite_of")

    def __repr__(self):
        return (
            f"<PrerequisiteRule service_id={self.service_id} "
            f"requires={self.prerequisite_service_id} mandatory={self.is_mandatory}>"
        )


# ── TABLE 4: user_services ─────────────────────────────────────────────────────

class UserService(Base):
    """
    Junction table tracking each user's engagement with a specific service.
    One row per (user, service) pair — enforced by UNIQUE constraint.

    Status lifecycle:
        NOT_STARTED → IN_PROGRESS → SUBMITTED → COMPLETED
                                               → REJECTED (can retry)

    Fields:
        id           : Auto-increment primary key
        user_id      : FK to users.id
        service_id   : FK to gov_services.id
        status       : Current lifecycle stage (see ServiceStatus enum)
        started_at   : When the user first engaged with this service
        completed_at : When status became COMPLETED or REJECTED
        notes        : Free-text notes (e.g. rejection reason, reference numbers)
        created_at   : Row creation timestamp
        updated_at   : Last update timestamp
    """
    __tablename__ = "user_services"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    service_id   = Column(Integer, ForeignKey("gov_services.id"), nullable=False, index=True)
    status       = Column(
        SAEnum(ServiceStatus, name="service_status_enum"),
        default=ServiceStatus.NOT_STARTED,
        nullable=False
    )
    started_at   = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes        = Column(Text, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Each user can have at most one record per service
    __table_args__ = (
        UniqueConstraint("user_id", "service_id", name="uq_user_service"),
    )

    # Relationships
    user    = relationship("User", back_populates="service_records")
    service = relationship("GovService", back_populates="user_records")
    steps   = relationship("Progress", back_populates="user_service", cascade="all, delete-orphan", order_by="Progress.step_number")

    def __repr__(self):
        return f"<UserService user={self.user_id} service={self.service_id} status='{self.status}'>"


# ── TABLE 5: progress ──────────────────────────────────────────────────────────

class Progress(Base):
    """
    Step-level checklist within a UserService record.
    Enables granular tracking of where a user is in a multi-step process.

    Example steps for "NID Registration":
        1. Fill out the NID application form (COMPLETED)
        2. Visit enrollment center for biometric capture (IN_PROGRESS)
        3. Collect NID card from office (PENDING)

    Fields:
        id               : Auto-increment primary key
        user_service_id  : FK to user_services.id
        step_number      : Ordered position of this step (1-indexed)
        step_name        : Short label (e.g. "Biometric Enrollment")
        step_name_ne     : Nepali short label
        step_description : Detailed instructions for the user
        step_description_ne : Nepali detailed instructions
        status           : Current state of this step (see StepStatus enum)
        completed_at     : When this step was marked COMPLETED or SKIPPED
        notes            : User notes or system messages for this step
    """
    __tablename__ = "progress"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_service_id = Column(Integer, ForeignKey("user_services.id"), nullable=False, index=True)
    step_number     = Column(Integer, nullable=False)
    step_name       = Column(String(200), nullable=False)
    step_name_ne    = Column(String(200), nullable=True)
    step_description = Column(Text, nullable=True)
    step_description_ne = Column(Text, nullable=True)
    status          = Column(
        SAEnum(StepStatus, name="step_status_enum"),
        default=StepStatus.PENDING,
        nullable=False
    )
    completed_at    = Column(DateTime(timezone=True), nullable=True)
    notes           = Column(Text, nullable=True)

    # Each (user_service, step_number) must be unique
    __table_args__ = (
        UniqueConstraint("user_service_id", "step_number", name="uq_progress_step"),
    )

    # Relationship
    user_service = relationship("UserService", back_populates="steps")

    def __repr__(self):
        return (
            f"<Progress user_service={self.user_service_id} "
            f"step={self.step_number} '{self.step_name}' status='{self.status}'>"
        )


# ── TABLE 6: documents ─────────────────────────────────────────────────────────

class Document(Base):
    """
    A file uploaded by a user (e.g. scanned citizenship, birth certificate,
    passport photo) stored in the app so it can be accessed from anywhere.

    Fields:
        id           : Auto-increment primary key
        user_id      : FK to users.id
        label        : Short user-friendly name the user gives the document
        tags         : Comma-separated labels/categories for searching/filtering
        description  : Optional free-text note
        filename     : Original filename (display only)
        stored_name  : Unique filename on disk (uuid + extension)
        mime_type    : Detected content type (image/jpeg, application/pdf, ...)
        size_bytes   : File size in bytes
        created_at   : When the document was uploaded
        updated_at   : Last metadata update
    """
    __tablename__ = "documents"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    label       = Column(String(200), nullable=False)
    tags        = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    filename    = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    mime_type   = Column(String(100), nullable=False)
    size_bytes  = Column(Integer, default=0, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="documents")

    def __repr__(self):
        return f"<Document id={self.id} user={self.user_id} label='{self.label}'>"


# ── TABLE 7: government_offices ────────────────────────────────────────────────

class GovernmentOffice(Base):
    """
    A curated catalog of real Nepali government offices where citizens
    complete the services EasyGov explains. This is static seed data — NOT a
    live Google Places search. It powers the "Find Nearest Office" feature.

    Fields:
        id            : Auto-increment primary key
        name          : Official office name (e.g. "Kathmandu District Administration Office")
        name_ne       : Nepali name (optional, for bilingual displays)
        office_type   : Short category, e.g. "District Administration Office",
                        "Department of Passports Office", "DoNIDCR Enrollment Center",
                        "Department of Transport Management"
        service_tags  : Comma-separated keys the /offices/nearby endpoint filters on.
                        Values align with service keys/categories used by the app:
                        citizenship, nid, passport, driving_license, identity, transport
        district      : Administrative district (e.g. "Kathmandu")
        address       : Street address (e.g. "Tripureshwor, Kathmandu")
        latitude      : WGS84 latitude
        longitude     : WGS84 longitude
        phone         : Published contact number (optional)
        hours         : Published service hours (optional, e.g. "10:00–17:00 Sun–Fri")
        is_active     : Soft-enable flag (False = hidden from results)
    """
    __tablename__ = "government_offices"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name         = Column(String(300), nullable=False, unique=True, index=True)
    name_ne      = Column(String(300), nullable=True)
    office_type  = Column(String(200), nullable=False)
    service_tags = Column(String(500), nullable=False, default="")
    district     = Column(String(150), nullable=False, index=True)
    address      = Column(String(500), nullable=False)
    latitude     = Column(Float, nullable=False)
    longitude    = Column(Float, nullable=False)
    phone        = Column(String(50), nullable=True)
    hours        = Column(String(100), nullable=True)
    is_active    = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<GovernmentOffice id={self.id} name='{self.name}' district='{self.district}'>"
