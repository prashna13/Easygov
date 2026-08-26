"""
seed_data.py
------------
Seed script for EasyGov Nepal database.

Populates the database with:
  - 7 government services (master catalog) — 4 active (Citizenship, NID,
    Passport, Driving License) with real guidance from the Nepal Essential
    Documents Guide; 3 retained as inactive (Bluebook, Business, Birth)
  - Prerequisite rules matching the document dependency chain
  - 1 test user (Prashna KC)
  - 2 user_service records for the test user with progress steps

Usage (from project root):
    python app/seed_data.py

This script is RE-RUNNABLE — existing services are updated in place, rules
are rebuilt, and user records are only inserted when missing.
"""

import sys
import os
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bcrypt

from app.database import SessionLocal
from app.models import (
    User, GovService, PrerequisiteRule,
    UserService, Progress, ServiceStatus, StepStatus,
    GovernmentOffice,
)
from app.nepali_content import SERVICE_NE, SEED_STEPS_NE
from app.office_seed_data import GOVERNMENT_OFFICES

def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ── SEED DATA DEFINITIONS ─────────────────────────────────────────────────────

GOV_SERVICES_DATA = [
    {
        "title":          "Citizenship Certificate Copy",
        "category":       "Identity",
        "description":    "Nepal's foundational identity document, issued by the District "
                          "Administration Office (DAO) on recommendation from your Ward Office. "
                          "Required before applying for NID, passport, driving license, banking, "
                          "and voting.",
        "department":     "District Administration Office (DAO)",
        "estimated_days": 3,
        "fee_npr":        10,
        "is_active":      True,
        "guidance": (
            "OVERVIEW\n"
            "The citizenship certificate is Nepal's foundational identity document. It is required "
            "before applying for NID, passport, driving license, opening bank accounts, property "
            "transactions, and voting. It is issued by the District Administration Office (DAO) under "
            "the Chief District Officer, based on a recommendation from your Ward Office. Main "
            "categories: by descent (the standard route), by birth, naturalized, and honorary.\n\n"
            "PREREQUISITES\n"
            "- You must be 16 years or older (for citizenship by descent).\n"
            "- At least one parent must hold Nepali citizenship.\n"
            "- Permanent residence must fall under the Ward Office/DAO jurisdiction where you apply; "
            "a migration certificate (Saruwa) is needed if you moved from another district.\n"
            "- Birth registration name and date of birth must match your parents' citizenship details "
            "exactly.\n\n"
            "DOCUMENTS NEEDED\n"
            "- Prescribed application form (Schedule-1), available at and certified by the Ward Office\n"
            "- Both parents' original citizenship certificates + photocopies\n"
            "- Birth registration certificate\n"
            "- School leaving/SEE certificate or a character certificate\n"
            "- Parents' marriage certificate\n"
            "- Ward Office recommendation letter\n"
            "- Two recent passport-size photographs\n"
            "- NPR 10 revenue stamp\n"
            "- An adult blood relative or ward resident who already holds citizenship (witness)\n"
            "- Migration certificate (Saruwa), only if applying outside the home district\n\n"
            "STEP-BY-STEP PROCEDURE\n"
            "1. Reconcile your records first — fix any name/DOB mismatch at the Ward Office before filing.\n"
            "2. Visit your local Ward Office with parents' citizenship certificates, your birth "
            "registration, school certificate, parents' marriage certificate, and photographs.\n"
            "3. Obtain the Ward Office recommendation letter certifying your identity and residence.\n"
            "4. Fill out the Schedule-1 application form and attach the revenue stamp.\n"
            "5. Submit the application at the DAO's citizenship section with your adult witness.\n"
            "6. Attend verification if a spot inquiry/police verification (Sarjaamin) is called.\n"
            "7. Receive your certificate — often the same day or within a few working days.\n\n"
            "FEES\n"
            "- First-time descent certificate: approx. NPR 10 (revenue stamp)\n"
            "- Duplicate/replacement certificate: approx. NPR 13\n"
            "- Fees can vary slightly by district — confirm at your local DAO.\n\n"
            "PROCESSING TIME\n"
            "- Same day to a few working days for straightforward descent applications.\n"
            "- Naturalization/honorary cases go through the Ministry of Home Affairs and Cabinet and "
            "can take several months.\n\n"
            "OFFICIAL RESOURCES\n"
            "- Ministry of Home Affairs: https://moha.gov.np\n"
            "- Nepal Law Commission (Citizenship Act 2063): https://lawcommission.gov.np\n"
            "- Your local District Administration Office (DAO)"
        ),
    },
    {
        "title":          "NID Registration",
        "category":       "Identity",
        "description":    "Biometric National Identity Card issued by DoNIDCR with a unique 10-digit "
                          "NIN. Mandatory for e-passport applications, banking, SIM registration, and "
                          "company registration.",
        "department":     "Department of National ID and Civil Registration (DoNIDCR)",
        "estimated_days": 45,
        "fee_npr":        0,
        "is_active":      True,
        "guidance": (
            "OVERVIEW\n"
            "The NID is a biometric smart card issued by the Department of National ID and Civil "
            "Registration (DoNIDCR). It stores your photograph, fingerprints, iris scan, and a unique "
            "10-digit National Identity Number (NIN). As of 2026, NID/NIN is mandatory for e-passport "
            "applications, banking, SIM registration, and company registration. It is intended to "
            "eventually replace the paper citizenship certificate.\n\n"
            "PREREQUISITES\n"
            "- Must be a Nepali citizen aged 16 or above.\n"
            "- Must hold a valid citizenship certificate (NID is issued based on it).\n"
            "- Foreigners residing in Nepal are not eligible.\n\n"
            "DOCUMENTS NEEDED\n"
            "- Original citizenship certificate (and photocopy)\n"
            "- Migration certificate, if applicable\n"
            "- Marriage certificate, if married\n"
            "- Death certificate of spouse, if applicable\n"
            "- Recent passport-size photograph (backup; biometric photo is captured live)\n"
            "- Mobile number for OTP verification\n\n"
            "STEP-BY-STEP PROCEDURE\n"
            "1. Go to the DoNIDCR pre-enrollment portal (https://donidcr.gov.np) and log in or create "
            "an account using your mobile number.\n"
            "2. Verify your number with the OTP sent via SMS.\n"
            "3. Start a 'New Enrollment' and fill in personal details — they must match your "
            "citizenship certificate exactly.\n"
            "4. Upload supporting documents (citizenship certificate, marriage certificate if applicable).\n"
            "5. Select your enrollment centre (typically your local DAO) and choose an appointment date.\n"
            "6. Print your pre-enrollment/token slip and keep it with your original documents.\n"
            "7. Attend your appointment in person — face and ears must be clearly visible (no heavy "
            "makeup, rings, hats, or face coverings).\n"
            "8. Complete biometric capture: photograph, fingerprints of all ten fingers, iris scan, "
            "and digital signature.\n"
            "9. Review your biometric report on the spot for errors.\n"
            "10. Receive an interim NIN confirmation, usable immediately while the card is printed.\n"
            "11. Collect your physical card when notified (weeks to months depending on backlog).\n"
            "12. No internet access? Walk into any DAO directly — staff fill the form on-site "
            "(longer queues).\n\n"
            "FEES\n"
            "- First-time enrollment: free\n"
            "- Replacement card (lost/damaged): approx. NPR 500\n\n"
            "PROCESSING TIME\n"
            "- Online pre-enrollment: same day\n"
            "- Biometric appointment: based on centre availability\n"
            "- Physical card delivery: a few weeks to a few months (large national backlog)\n\n"
            "OFFICIAL RESOURCES\n"
            "- DoNIDCR: https://donidcr.gov.np\n"
            "- Nagarik App (for digital NID access) on Google Play / App Store"
        ),
    },
    {
        "title":          "E-Passport Apply",
        "category":       "Identity",
        "description":    "Nepal's ICAO-compliant biometric e-Passport issued by the Department of "
                          "Passports. Apply online, then attend an in-person appointment for "
                          "biometrics at the Department, any DAO, or an embassy abroad.",
        "department":     "Department of Passports",
        "estimated_days": 30,
        "fee_npr":        5000,
        "is_active":      True,
        "guidance": (
            "OVERVIEW\n"
            "Nepal's biometric e-Passport is issued by the Department of Passports under the Ministry "
            "of Foreign Affairs, governed by the Passport Act 2076 and Passport Rules 2077. It is "
            "compliant with the ICAO Doc 9303 standard. Applications can be made at the Department of "
            "Passports (Kathmandu), any District Administration Office (DAO), or Nepali embassies and "
            "consulates abroad.\n\n"
            "PREREQUISITES\n"
            "- Must be a Nepali citizen with a valid citizenship certificate.\n"
            "- Must have a National Identity Number (NID/NIN) — compulsory for applications and renewals.\n"
            "- For minors, a birth certificate or Minor Identity Card is required instead of a "
            "citizenship certificate.\n\n"
            "DOCUMENTS NEEDED\n"
            "- Original citizenship certificate + photocopy\n"
            "- National Identity Number (NID/NIN)\n"
            "- Printed copy of the completed online pre-enrollment form\n"
            "- Old passport (original), if renewing/re-issuing\n"
            "- Two recent passport-size photographs (white background)\n"
            "- Payment receipt/bank voucher for the applicable fee\n"
            "- For lost passports: police report (FIR) and a notice in a national daily\n"
            "- For applicants abroad: valid visa/residency proof\n\n"
            "STEP-BY-STEP PROCEDURE\n"
            "1. Complete the online pre-enrollment form at https://emrtds.nepalpassport.gov.np.\n"
            "2. Select your preferred office: Department of Passports HQ, a DAO, or an embassy/consulate.\n"
            "3. Choose an appointment date and time slot.\n"
            "4. Pay the applicable fee and print your pre-enrollment slip.\n"
            "5. Appear in person on your appointment date with all original documents.\n"
            "6. Biometric capture on-site: live photo, fingerprints, and document verification.\n"
            "7. Wait for processing (DAOs typically 7–15 working days; embassies 4–8 weeks).\n"
            "8. Collect your passport from the office where you applied; provincial DAOs add ~5–7 days "
            "for transport from Kathmandu.\n"
            "9. Renewal: apply for a new passport to replace the old one — recommended when less than "
            "6 months of validity remains.\n"
            "10. Lost passport: file a police FIR, publish a loss notice in a national daily, then "
            "apply with these as additional documents.\n\n"
            "FEES (regular Nepal e-Passport — verify current rates on the official site)\n"
            "- 34-page regular: NPR 5,000 | 34-page fast-track: NPR 12,000\n"
            "- 66-page regular: NPR 10,000 | 66-page fast-track: NPR 20,000\n"
            "- Minor under 10, 34-page: NPR 9,500\n"
            "- Abroad: approx. USD 50–150\n\n"
            "PROCESSING TIME\n"
            "- Regular: 15–30 working days\n"
            "- Urgent/fast-track: 2–5 working days\n"
            "- Embassy/consulate abroad: 4–8 weeks\n\n"
            "OFFICIAL RESOURCES\n"
            "- Department of Passports: https://nepalpassport.gov.np\n"
            "- Pre-enrollment portal: https://emrtds.nepalpassport.gov.np\n"
            "- Ministry of Foreign Affairs: https://mofa.gov.np\n"
            "- Passport tracking via the official portal using your receipt/pre-enrollment ID"
        ),
    },
    {
        "title":          "Driving License",
        "category":       "Transport",
        "description":    "Nepali driving license issued by the Department of Transport Management "
                          "(DoTM). Categories A (motorcycle) and B (car). Process: online application, "
                          "written exam, and a practical trial test.",
        "department":     "Department of Transport Management (DoTM)",
        "estimated_days": 30,
        "fee_npr":        2000,
        "is_active":      True,
        "guidance": (
            "OVERVIEW\n"
            "Driving licenses in Nepal are issued by the Department of Transport Management (DoTM) "
            "under the Motor Vehicles and Transport Management Act 2049. Common categories include "
            "Category A (motorcycle/scooter) and Category B (car/jeep), with higher categories (C, D, "
            "E) for commercial and heavy vehicles. The process involves an online application, a "
            "written exam, and a practical trial (road test).\n\n"
            "PREREQUISITES\n"
            "- Minimum age: 16 years for Category A (motorcycle); 18 years for Category B (car/jeep); "
            "21 years for heavy vehicle categories (D, E).\n"
            "- Must hold a valid citizenship certificate.\n"
            "- Must pass a written knowledge test and a practical trial test (minimum 70/100 points).\n"
            "- A lower category license is required before applying for certain higher categories.\n\n"
            "DOCUMENTS NEEDED\n"
            "- Original Nepali citizenship certificate + photocopy\n"
            "- Blood group certificate from a recognized medical centre/hospital\n"
            "- Eye test/vision certificate from a registered eye specialist (Category B and above)\n"
            "- Medical/fitness certificate from a registered doctor\n"
            "- Two recent passport-size photographs (white background)\n"
            "- National ID/NIN — used to auto-fill the online application via QR scan\n"
            "- Payment receipt for the applicable government fee\n\n"
            "STEP-BY-STEP PROCEDURE\n"
            "1. Register/log in at the DoTM portal https://applydlnew.dotm.gov.np (or via Nagarik App).\n"
            "2. Complete your profile; scan the QR code on your NID to auto-fill much of the form.\n"
            "3. Select your license category (A for motorcycle, B for car, etc.) — you can apply for "
            "more than one category at once.\n"
            "4. Upload required documents: citizenship, blood group certificate, eye test certificate "
            "(Category B+), photographs.\n"
            "5. Pay the government fee online.\n"
            "6. Book an appointment at your chosen Transport Management Office (any office nationwide).\n"
            "7. Visit the office on your appointment date with original documents for verification and "
            "biometric enrollment.\n"
            "8. Sit the written exam at the office (or a computer-based test in some regions).\n"
            "9. If you pass, you'll be scheduled for the practical trial test (minimum ~70 points).\n"
            "10. You get up to three trial attempts within 18 months of passing the written exam; "
            "failing all three means reapplying after a 90-day wait.\n"
            "11. After passing both tests, pay the final license issuance fee.\n"
            "12. Receive a temporary driving slip while the smart card prints (SMS notification when "
            "ready) — the slip legally permits you to drive.\n"
            "13. Collect your license at the office, or check if mail delivery is available in your "
            "area.\n\n"
            "FEES (indicative — verify current rates at dotm.gov.np)\n"
            "- Motorcycle/scooter (Category A): approx. NPR 1,500\n"
            "- Car/jeep (Category B): approx. NPR 2,000\n"
            "- Renewal: similar fee structure, required every 5 years\n\n"
            "PROCESSING TIME\n"
            "- Written exam: scheduled shortly after document verification\n"
            "- Trial test: scheduled after passing the written exam\n"
            "- Smart card printing/delivery: typically 15–30 working days after passing both tests\n\n"
            "RENEWAL\n"
            "- Renew online in the final year of validity at https://applydlnew.dotm.gov.np.\n"
            "- Requires a fresh medical certificate (dated within 3 months) and the original license.\n"
            "- Some offices still require an in-person visit; Kathmandu offices are increasingly "
            "fully online.\n\n"
            "OFFICIAL RESOURCES\n"
            "- DoTM: https://dotm.gov.np\n"
            "- Application portal: https://applydlnew.dotm.gov.np\n"
            "- License verification via dotm.gov.np (DOB + license number)\n"
            "- Complaints/support: gunaso@dotm.gov.np"
        ),
    },
    {
        "title":          "Bluebook Renewal",
        "category":       "Transport",
        "description":    "Renew your vehicle registration booklet (Bluebook). Requires payment of "
                          "provincial road tax and passing a vehicle inspection.",
        "department":     "Department of Transport Management (DOTM)",
        "estimated_days": 7,
        "fee_npr":        1500,
        "is_active":      False,
        "guidance":       None,
    },
    {
        "title":          "Business Registration",
        "category":       "Business",
        "description":    "Register a new business entity with the Office of Company Registrar. "
                          "Covers sole proprietorship, partnership, and private limited companies.",
        "department":     "Office of Company Registrar (OCR)",
        "estimated_days": 14,
        "fee_npr":        3000,
        "is_active":      True,
        "guidance":       (
            "OVERVIEW\n"
            "Business (company) registration is the legal incorporation of a business entity with the "
            "Office of Company Registrar (OCR), under the Companies Act 2063 and Companies Regulations "
            "2064. A registered company is a separate legal entity: it can own property, open bank "
            "accounts, enter contracts, and sue or be sued in its own name, and shareholders' personal "
            "liability is limited to their investment. The entire process is done online through the CAMIS "
            "portal (Company Administration and Management Information System). For most startups and "
            "small businesses the fastest, cheapest and simplest structure is a Private Limited Company.\n\n"
            "PREREQUISITES\n"
            "- A proposed company name (check availability on CAMIS in English and Nepali)\n"
            "- Minimum 1 shareholder for a Private Limited Company (7 for a Public Limited Company)\n"
            "- Minimum paid-up capital NPR 1,00,000 (1 Lakh) for a Private Limited Company\n"
            "- A physical registered-office address with proof (a PO Box is not accepted)\n"
            "- For foreign investment (FDI): approval from the Department of Industry (DOI) or Investment "
            "Board Nepal (IBN), and minimum investment of NPR 2,00,00,000 (2 Crore) per foreign investor\n\n"
            "DOCUMENTS NEEDED\n"
            "- Application Form (Anusuchi 1) as per OCR format, with an NPR 5 revenue stamp\n"
            "- Memorandum of Association (MOA / Prabandha Patra) - two signed copies\n"
            "- Articles of Association (AOA / Niyamawali) - two signed copies\n"
            "- Attested copies of the citizenship certificates of all promoters / shareholders\n"
            "- Proof of the registered office address (rental agreement or ownership document)\n"
            "- Passport-size photographs of all promoters / directors\n"
            "- Mutual agreement among shareholders (if there are multiple promoters)\n"
            "- Written consent letters from each director\n\n"
            "STEP-BY-STEP PROCEDURE\n"
            "1. Create an account on the CAMIS portal at https://camis.ocr.gov.np/login and verify it by email.\n"
            "2. Reserve the company name: log in, search name availability, and submit up to 3 ranked "
            "proposed names. Approval or rejection is emailed within 1-3 working days; an approved name is "
            "valid for 90 days.\n"
            "3. Prepare the Memorandum of Association (MOA) and Articles of Association (AOA) - two signed "
            "copies of each, in Nepali or English. A legal consultant or company secretary is recommended.\n"
            "4. Submit the online application on CAMIS: enter shareholders, directors, registered office "
            "address, authorized capital, number of shares and face value, and upload scanned copies of all "
            "required documents (PDF or JPEG).\n"
            "5. Review and query resolution: OCR officers check for completeness and compliance. If there "
            "are discrepancies, OCR raises a query via CAMIS - respond within 7 days to avoid rejection.\n"
            "6. Pay the registration fee: a payment notice is generated on CAMIS. Pay online via e-banking, "
            "eSewa, Khalti or card. Fees above NPR 5,000 require a bank deposit and uploaded voucher. Keep "
            "the receipt.\n"
            "7. Download the Certificate of Incorporation from CAMIS once payment and final verification are "
            "complete - this is your company's legal identity document.\n\n"
            "FEES\n"
            "- Private Limited Company: NPR 1,000 for authorized capital up to NPR 1,00,000, rising to "
            "NPR 4,500 (1-5 lakh), NPR 9,500 (5-10 lakh), NPR 13,500 (10-20 lakh), NPR 21,500 (20-50 lakh), "
            "NPR 29,500 (50 lakh-1 crore), NPR 43,500 (1-10 crore), and NPR 43,500 plus NPR 4,000 per "
            "additional 10 lakh above that.\n"
            "- Fast-track / urgent registration carries a 50% surcharge on the government fee.\n"
            "- Budget extra costs: MOA/AOA drafting (NPR 3,000-10,000), notarisation (NPR 500-2,000), Ward "
            "Office registration (NPR 5,000-15,000), PAN registration at IRD (free), VAT registration (free, "
            "if applicable), and a company seal (NPR 500-1,500).\n\n"
            "PROCESSING TIME\n"
            "- Name reservation: 1-3 working days\n"
            "- OCR document review: 5-10 working days\n"
            "- Query resolution (if raised): 7 days from the notice\n"
            "- Total with complete documents and no queries: 7-10 working days\n"
            "- Total with queries or corrections: up to 21 working days\n"
            "- FDI companies with DOI/IBN approval: 4-8 weeks additional\n\n"
            "POST-REGISTRATION COMPLIANCE (MANDATORY)\n"
            "- Register for PAN within 7 days at the Inland Revenue Department (IRD)\n"
            "- Register the business at the Ward Office within 30 days\n"
            "- Hold the first board meeting within 30 days\n"
            "- Issue share certificates within 60 days\n"
            "- File the Share Lagat (shareholder details) with OCR within 90 days\n"
            "- Open a company bank account as soon as possible\n"
            "- Register for VAT if the turnover threshold applies\n"
            "- Appoint an auditor and notify OCR within 15 days of appointment\n\n"
            "OFFICIAL RESOURCES\n"
            "- CAMIS Portal: https://camis.ocr.gov.np\n"
            "- Office of Company Registrar: https://ocr.gov.np\n"
            "- Inland Revenue Department (PAN/VAT): https://ird.gov.np\n"
            "- Department of Industry (FDI): https://doind.gov.np\n"
        ),
    },
    {
        "title":          "Birth Certificate",
        "category":       "Identity",
        "description":    "Register a birth and obtain an official birth certificate from the local "
                          "ward office. Required within 35 days of birth (free); late registration "
                          "attracts a fee.",
        "department":     "Local Ward Office",
        "estimated_days": 2,
        "fee_npr":        0,
        "is_active":      False,
        "guidance":       None,
    },
]

# Merge auto-generated Nepali translations into the service definitions.
for _svc in GOV_SERVICES_DATA:
    _ne = SERVICE_NE.get(_svc["title"])
    if _ne:
        _svc["title_ne"] = _ne["title"]
        _svc["category_ne"] = _ne["category"]
        _svc["description_ne"] = _ne["description"]
        _svc["guidance_ne"] = _ne["guidance"]

# Maps (service_title, prerequisite_title, is_mandatory, notes)
# Citizenship is the root document; NID builds on it; passport and driving
# license come last. Mirrors the Nepal Essential Documents Guide.
PREREQUISITE_RULES_DATA = [
    (
        "NID Registration",
        "Citizenship Certificate Copy",
        True,
        "DoNIDCR uses the citizenship certificate as the base identifier for NID enrollment."
    ),
    (
        "E-Passport Apply",
        "Citizenship Certificate Copy",
        True,
        "Department of Passports requires a valid citizenship certificate as primary identity proof."
    ),
    (
        "E-Passport Apply",
        "NID Registration",
        True,
        "A National Identity Number (NID/NIN) is now compulsory for e-passport applications."
    ),
    (
        "Driving License",
        "Citizenship Certificate Copy",
        True,
        "DoTM requires a valid citizenship certificate for all license categories."
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
    "age":                28,
    "onboarding_completed": True,
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

# Merge auto-generated Nepali step translations into the seeded step definitions.
for _steps, _ne_steps in (
    (NID_STEPS, SEED_STEPS_NE["NID_STEPS"]),
    (CITIZENSHIP_STEPS, SEED_STEPS_NE["CITIZENSHIP_STEPS"]),
):
    for _s, _ne in zip(_steps, _ne_steps):
        _s["step_name_ne"] = _ne[0]
        _s["step_description_ne"] = _ne[1]


# ── SEED FUNCTIONS ────────────────────────────────────────────────────────────

def seed_services(db) -> dict:
    """Upsert gov_services from the seed data. Returns title→GovService map."""
    print("\n[SERVICES] Seeding government services...")
    service_map = {}
    for svc_data in GOV_SERVICES_DATA:
        title = svc_data["title"]
        existing = db.query(GovService).filter_by(title=title).first()
        if existing:
            # Update the existing record in place so the seed stays authoritative.
            for field, value in svc_data.items():
                setattr(existing, field, value)
            print(f"   [UPDATED] '{title}'")
            service_map[title] = existing
        else:
            svc = GovService(**svc_data)
            db.add(svc)
            db.flush()  # Get the generated id before committing
            service_map[title] = svc
            print(f"   [ADDED] '{title}'")
    db.commit()
    return service_map


def seed_government_offices(db):
    """Upsert the curated government-office catalog by name (idempotent)."""
    print("\n[OFFICES] Seeding government offices...")
    for data in GOVERNMENT_OFFICES:
        name = data["name"]
        existing = db.query(GovernmentOffice).filter_by(name=name).first()
        if existing:
            for field, value in data.items():
                setattr(existing, field, value)
            print(f"   [UPDATED] '{name}'")
        else:
            db.add(GovernmentOffice(**data))
            print(f"   [ADDED] '{name}'")
    db.commit()
    print(f"   [OK] {len(GOVERNMENT_OFFICES)} office(s) in catalog")


def seed_prerequisite_rules(db, service_map: dict):
    """Rebuild prerequisite rules to match the current dependency chain."""
    print("\n[RULES] Rebuilding prerequisite rules...")
    # Clear old rules first so removed dependencies (e.g. citizenship→birth)
    # don't linger and break the chain.
    deleted = db.query(PrerequisiteRule).delete()
    print(f"   [CLEARED] {deleted} old rule(s)")

    for service_title, prereq_title, is_mandatory, notes in PREREQUISITE_RULES_DATA:
        service = service_map.get(service_title)
        prereq  = service_map.get(prereq_title)
        if not service or not prereq:
            print(f"   [SKIP] rule '{service_title}' -> '{prereq_title}' (service not found)")
            continue

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
        # Backfill profile fields added after this user was first seeded so
        # the demo profile stays complete (age, onboarding, DOB, address).
        existing.age = TEST_USER.get("age", existing.age)
        existing.date_of_birth = TEST_USER.get("date_of_birth", existing.date_of_birth)
        existing.address = TEST_USER.get("address", existing.address)
        existing.onboarding_completed = TEST_USER.get("onboarding_completed", existing.onboarding_completed)
        db.commit()
        print(f"   [UPDATED] User '{existing.email}' (profile backfilled)")
        return existing

    user = User(
        full_name          = TEST_USER["full_name"],
        email              = TEST_USER["email"],
        phone              = TEST_USER["phone"],
        password_hash      = hash_password(TEST_USER["password"]),
        citizenship_number = TEST_USER["citizenship_number"],
        date_of_birth      = TEST_USER["date_of_birth"],
        age                = TEST_USER.get("age"),
        address            = TEST_USER["address"],
        province           = TEST_USER["province"],
        onboarding_completed = TEST_USER.get("onboarding_completed", False),
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

        # Upsert the seeded steps (fills any missing Nepali translations).
        for step_data in CITIZENSHIP_STEPS:
            step = (
                db.query(Progress)
                .filter_by(user_service_id=us_citizenship.id, step_number=step_data["step_number"])
                .first()
            )
            if step is None:
                step = Progress(user_service_id=us_citizenship.id, **step_data)
                db.add(step)
            else:
                for field, value in step_data.items():
                    setattr(step, field, value)
            print(f"      - Step {step_data['step_number']}: '{step_data['step_name']}' [{step_data['status'].value}]")

    # ── Record 2: NID Registration (IN_PROGRESS) ─────────────────────────────
    nid_svc = service_map.get("NID Registration")
    if nid_svc:
        existing = db.query(UserService).filter_by(
            user_id=user.id, service_id=nid_svc.id
        ).first()

        if existing:
            print(f"   [SKIP] UserService for 'NID Registration' (already exists)")
            us_nid = existing
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

        # Upsert the seeded steps (fills any missing Nepali translations).
        for step_data in NID_STEPS:
            step = (
                db.query(Progress)
                .filter_by(user_service_id=us_nid.id, step_number=step_data["step_number"])
                .first()
            )
            if step is None:
                step = Progress(user_service_id=us_nid.id, **step_data)
                db.add(step)
            else:
                for field, value in step_data.items():
                    setattr(step, field, value)
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
        seed_government_offices(db)
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
