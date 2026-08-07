"""
seed_data.py
------------
Seed script for EasyGov Nepal database.

Populates the database with:
  - 6 government services (master catalog)
  - 4 prerequisite rules
  - 1 test user (Prashna KC)
  - 2 user_service records for the test user
  - 3 progress steps for the NID service

Usage (from project root):
    python app/seed_data.py

This script is RE-RUNNABLE — it checks for existing records before inserting,
so running it twice won't create duplicates.
"""

import sys
import os
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bcrypt

from app.database import SessionLocal, engine, Base
from app.models import (
    User, GovService, PrerequisiteRule,
    UserService, Progress, ServiceStatus, StepStatus
)

def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ── SEED DATA DEFINITIONS ─────────────────────────────────────────────────────

GOV_SERVICES_DATA = [
    {
        "title":          "Citizenship Certificate Copy",
        "category":       "Identity",
        "description":    "Obtain a certified copy of your Nepal citizenship certificate. "
                          "This is a foundational document required for most other government services.",
        "department":     "District Administration Office (DAO)",
        "estimated_days": 3,
        "fee_npr":        100,
    },
    {
        "title":          "NID Registration",
        "category":       "Identity",
        "description":    "National Identity Card biometric enrollment. Requires in-person visit "
                          "to enrollment center for fingerprinting and photo. Card issued within 30 days.",
        "department":     "Department of National ID and Civil Registration (DONIDCR)",
        "estimated_days": 30,
        "fee_npr":        0,
    },
    {
        "title":          "E-Passport Apply",
        "category":       "Identity",
        "description":    "Apply for Nepal's biometric e-passport. Includes pre-enrollment online "
                          "and in-person appointment at the Department of Passports.",
        "department":     "Department of Passports",
        "estimated_days": 45,
        "fee_npr":        5000,
    },
    {
        "title":          "Bluebook Renewal",
        "category":       "Transport",
        "description":    "Renew your vehicle registration booklet (Bluebook). Requires payment of "
                          "provincial road tax and passing a vehicle inspection.",
        "department":     "Department of Transport Management (DOTM)",
        "estimated_days": 7,
        "fee_npr":        1500,
    },
    {
        "title":          "Business Registration",
        "category":       "Business",
        "description":    "Register a new business entity with the Office of Company Registrar. "
                          "Covers sole proprietorship, partnership, and private limited companies.",
        "department":     "Office of Company Registrar (OCR)",
        "estimated_days": 14,
        "fee_npr":        3000,
    },
    {
        "title":          "Birth Certificate",
        "category":       "Identity",
        "description":    "Register a birth and obtain an official birth certificate from the local "
                          "ward office. Required within 35 days of birth (free); late registration attracts a fee.",
        "department":     "Local Ward Office",
        "estimated_days": 2,
        "fee_npr":        0,
    },
]

# Maps (service_title, prerequisite_title, is_mandatory, notes)
PREREQUISITE_RULES_DATA = [
    (
        "E-Passport Apply",
        "Citizenship Certificate Copy",
        True,
        "Department of Passports requires a valid citizenship certificate as primary identity proof."
    ),
    (
        "NID Registration",
        "Citizenship Certificate Copy",
        True,
        "DONIDCR uses citizenship number as the base identifier for NID enrollment."
    ),
    (
        "Business Registration",
        "Citizenship Certificate Copy",
        True,
        "OCR requires citizenship copy for all company founders/directors."
    ),
    (
        "Bluebook Renewal",
        "NID Registration",
        False,
        "NID is accepted as a valid ID at DOTM offices. Alternatively, passport or citizenship copy can be used."
    ),
]

TEST_USER = {
    "full_name":          "Prashna KC",
    "email":              "prashna@easygov.np",
    "phone":              "+977-9812345678",
    "password":           "password123",          # will be bcrypt-hashed
    "citizenship_number": "12-01-78-12345",
    "date_of_birth":      date(1998, 3, 15),
    "address":            "Ward 5, Lalitpur Metropolitan City",
    "province":           "Bagmati Province",
}

# Steps seeded for NID Registration (IN_PROGRESS)
NID_STEPS = [
    {
        "step_number":    1,
        "step_name":      "Fill NID Application Form",
        "step_description": (
            "Complete the online NID application form at donidcr.gov.np. "
            "You will need your citizenship number and a recent passport photo."
        ),
        "status":         StepStatus.COMPLETED,
        "completed_at":   datetime(2026, 7, 20, 10, 30, tzinfo=timezone.utc),
        "notes":          "Application reference: NID-2026-88412",
    },
    {
        "step_number":    2,
        "step_name":      "Biometric Enrollment",
        "step_description": (
            "Visit your nearest NID enrollment center for fingerprinting and photograph. "
            "Bring your citizenship certificate and the application reference number."
        ),
        "status":         StepStatus.IN_PROGRESS,
        "completed_at":   None,
        "notes":          "Appointment scheduled for 2026-08-10 at Lalitpur Enrollment Center.",
    },
    {
        "step_number":    3,
        "step_name":      "Collect NID Card",
        "step_description": (
            "After biometric processing (approx. 30 days), collect your NID card "
            "from the enrollment center. Bring your application reference number."
        ),
        "status":         StepStatus.PENDING,
        "completed_at":   None,
        "notes":          None,
    },
]

# Steps seeded for Citizenship Certificate Copy (COMPLETED)
CITIZENSHIP_STEPS = [
    {
        "step_number":    1,
        "step_name":      "Submit Application at DAO",
        "step_description": "Visit the District Administration Office with original citizenship, 2 passport photos, and fee receipt.",
        "status":         StepStatus.COMPLETED,
        "completed_at":   datetime(2026, 6, 5, 9, 0, tzinfo=timezone.utc),
        "notes":          "Submitted at Lalitpur DAO.",
    },
    {
        "step_number":    2,
        "step_name":      "Collect Certified Copy",
        "step_description": "Return after 3 working days to collect your certified citizenship copy.",
        "status":         StepStatus.COMPLETED,
        "completed_at":   datetime(2026, 6, 9, 11, 0, tzinfo=timezone.utc),
        "notes":          "Collected successfully. Document stored safely.",
    },
]


# ── SEED FUNCTIONS ────────────────────────────────────────────────────────────

def seed_services(db) -> dict:
    """Insert gov_services if they don't exist. Returns title→GovService map."""
    print("\n[SERVICES] Seeding government services...")
    service_map = {}
    for svc_data in GOV_SERVICES_DATA:
        existing = db.query(GovService).filter_by(title=svc_data["title"]).first()
        if existing:
            print(f"   [SKIP] '{svc_data['title']}' (already exists)")
            service_map[svc_data["title"]] = existing
        else:
            svc = GovService(**svc_data)
            db.add(svc)
            db.flush()  # Get the generated id before committing
            service_map[svc_data["title"]] = svc
            print(f"   [ADDED] '{svc_data['title']}'")
    db.commit()
    return service_map


def seed_prerequisite_rules(db, service_map: dict):
    """Insert prerequisite rules if they don't exist."""
    print("\n[RULES] Seeding prerequisite rules...")
    for service_title, prereq_title, is_mandatory, notes in PREREQUISITE_RULES_DATA:
        service = service_map.get(service_title)
        prereq  = service_map.get(prereq_title)
        if not service or not prereq:
            print(f"   [SKIP] rule '{service_title}' -> '{prereq_title}' (service not found)")
            continue

        existing = db.query(PrerequisiteRule).filter_by(
            service_id=service.id,
            prerequisite_service_id=prereq.id
        ).first()

        if existing:
            print(f"   [SKIP] '{service_title}' requires '{prereq_title}' (already exists)")
        else:
            rule = PrerequisiteRule(
                service_id=service.id,
                prerequisite_service_id=prereq.id,
                is_mandatory=is_mandatory,
                notes=notes,
            )
            db.add(rule)
            mandatory_label = "MANDATORY" if is_mandatory else "OPTIONAL"
            print(f"   [ADDED] '{service_title}' requires '{prereq_title}' [{mandatory_label}]")

    db.commit()


def seed_test_user(db) -> User:
    """Insert the test user if they don't exist."""
    print("\n[USER] Seeding test user...")
    existing = db.query(User).filter_by(email=TEST_USER["email"]).first()
    if existing:
        print(f"   [SKIP] User '{TEST_USER['email']}' (already exists)")
        return existing

    user = User(
        full_name          = TEST_USER["full_name"],
        email              = TEST_USER["email"],
        phone              = TEST_USER["phone"],
        password_hash      = hash_password(TEST_USER["password"]),
        citizenship_number = TEST_USER["citizenship_number"],
        date_of_birth      = TEST_USER["date_of_birth"],
        address            = TEST_USER["address"],
        province           = TEST_USER["province"],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"   [ADDED] User '{user.email}' (id={user.id})")
    return user


def seed_user_services(db, user: User, service_map: dict):
    """Insert user_service records and their progress steps."""
    print("\n[PROGRESS] Seeding user service records...")

    # ── Record 1: Citizenship Certificate Copy (COMPLETED) ──────────────────
    citizenship_svc = service_map.get("Citizenship Certificate Copy")
    if citizenship_svc:
        existing = db.query(UserService).filter_by(
            user_id=user.id, service_id=citizenship_svc.id
        ).first()

        if existing:
            print(f"   [SKIP] UserService for 'Citizenship Certificate Copy' (already exists)")
            us_citizenship = existing
        else:
            us_citizenship = UserService(
                user_id      = user.id,
                service_id   = citizenship_svc.id,
                status       = ServiceStatus.COMPLETED,
                started_at   = datetime(2026, 6, 5, 9, 0, tzinfo=timezone.utc),
                completed_at = datetime(2026, 6, 9, 11, 0, tzinfo=timezone.utc),
                notes        = "Obtained certified copy from Lalitpur DAO.",
            )
            db.add(us_citizenship)
            db.flush()
            print(f"   [ADDED] UserService: 'Citizenship Certificate Copy' -> COMPLETED")

            for step_data in CITIZENSHIP_STEPS:
                step = Progress(user_service_id=us_citizenship.id, **step_data)
                db.add(step)
                print(f"      - Step {step_data['step_number']}: '{step_data['step_name']}' [{step_data['status'].value}]")

    # ── Record 2: NID Registration (IN_PROGRESS) ─────────────────────────────
    nid_svc = service_map.get("NID Registration")
    if nid_svc:
        existing = db.query(UserService).filter_by(
            user_id=user.id, service_id=nid_svc.id
        ).first()

        if existing:
            print(f"   [SKIP] UserService for 'NID Registration' (already exists)")
        else:
            us_nid = UserService(
                user_id    = user.id,
                service_id = nid_svc.id,
                status     = ServiceStatus.IN_PROGRESS,
                started_at = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc),
                notes      = "Biometric appointment scheduled for 2026-08-10.",
            )
            db.add(us_nid)
            db.flush()
            print(f"   [ADDED] UserService: 'NID Registration' -> IN_PROGRESS")

            for step_data in NID_STEPS:
                step = Progress(user_service_id=us_nid.id, **step_data)
                db.add(step)
                print(f"      - Step {step_data['step_number']}: '{step_data['step_name']}' [{step_data['status'].value}]")

    db.commit()


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run_seed():
    print("=" * 60)
    print("  EasyGov Nepal — Database Seed Script")
    print("=" * 60)

    db = SessionLocal()
    try:
        service_map = seed_services(db)
        seed_prerequisite_rules(db, service_map)
        test_user   = seed_test_user(db)
        seed_user_services(db, test_user, service_map)

        print("\n" + "=" * 60)
        print("[OK] Seeding complete!")
        print()
        print("[LOGIN] Test Login Credentials:")
        print(f"   Email    : {TEST_USER['email']}")
        print(f"   Password : {TEST_USER['password']}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
