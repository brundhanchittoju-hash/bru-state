import json
from datetime import date
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.audit_case import AuditCase
from app.models.system import Holiday, Setting
from app.models.user import Department, Role, User
from app.services.audit_trail import log_activity


def seed(db_session: Session = None):
    should_close = False
    if db_session is not None:
        db = db_session
    else:
        db = SessionLocal()
        should_close = True
    try:
        print("[SEED] Seeding Karnataka State Audit Department Demo Data...")

        # 1. Seed Roles
        roles_data = [
            ("administrator", "Administrator", "System configuration, user administration, security auditing"),
            ("audit_officer", "Audit Officer", "Final review, statutory approval, finding settlement, report release"),
            ("senior_auditor", "Senior Auditor", "Case review, lead auditor assignment, finding review, rule overrides"),
            ("auditor", "Auditor", "Field verification, document ingestion, voucher inspection, finding proposals"),
        ]
        roles_map = {}
        for code, name, desc in roles_data:
            role = db.query(Role).filter(Role.code == code).first()
            if not role:
                role = Role(code=code, name=name, description=desc)
                db.add(role)
                db.commit()
                db.refresh(role)
            roles_map[code] = role
        print("[OK] Roles seeded.")

        # 2. Seed Departments
        dept_data = [
            ("KSAD_HQ", "Karnataka State Audit Department (Headquarters)", "State", "Bengaluru Urban", None),
            ("RDPR_STATE", "Rural Development and Panchayat Raj Department", "State", "Bengaluru Urban", None),
            ("ZP_MYS", "Mysuru Zilla Panchayat", "Zilla Panchayat", "Mysuru", None),
            ("ZP_BEL", "Belagavi Zilla Panchayat", "Zilla Panchayat", "Belagavi", None),
            ("ZP_DHA", "Dharwad Zilla Panchayat", "Zilla Panchayat", "Dharwad", None),
            ("ZP_TUM", "Tumakuru Zilla Panchayat", "Zilla Panchayat", "Tumakuru", None),
            ("ZP_KAL", "Kalaburagi Zilla Panchayat", "Zilla Panchayat", "Kalaburagi", None),
        ]
        dept_map = {}
        for code, name, dtype, dist, pid in dept_data:
            dept = db.query(Department).filter(Department.code == code).first()
            if not dept:
                dept = Department(code=code, name=name, type=dtype, district=dist, parent_id=pid)
                db.add(dept)
                db.commit()
                db.refresh(dept)
            dept_map[code] = dept
        print("[OK] Departments seeded.")

        # 3. Seed Demo Users
        users_data = [
            ("admin@stateaudit.kar.gov.in", "AdminPassword@2024", "Ramesh Kumar (Admin)", "administrator", "KSAD_HQ"),
            ("officer@stateaudit.kar.gov.in", "OfficerPassword@2024", "Suresh Patil, KAS (Audit Officer)", "audit_officer", "KSAD_HQ"),
            ("senior.auditor@stateaudit.kar.gov.in", "SeniorPassword@2024", "Vidya Hegde (Senior Auditor)", "senior_auditor", "ZP_MYS"),
            ("auditor@stateaudit.kar.gov.in", "AuditorPassword@2024", "Anand Rao (Auditor)", "auditor", "ZP_MYS"),
        ]
        user_map = {}
        for email, pwd, name, rcode, dcode in users_data:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    hashed_password=get_password_hash(pwd),
                    full_name=name,
                    role_id=roles_map[rcode].id,
                    department_id=dept_map[dcode].id,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            user_map[email] = user
        print("[OK] Demo Users seeded.")

        # 4. Seed Settings
        settings_data = [
            (
                "local_body_terms",
                json.dumps({
                    "state": "Karnataka",
                    "tier1": "Zilla Panchayat",
                    "tier2": "Taluk Panchayat",
                    "tier3": "Taluk",
                    "tier4": "Gram Panchayat",
                }),
                "governance",
                True,
            ),
            (
                "currency_locale",
                json.dumps({
                    "currency": "INR",
                    "symbol": "₹",
                    "locale": "en-IN",
                    "grouping": "lakh_crore",
                }),
                "localization",
                False,
            ),
            (
                "audit_department_info",
                json.dumps({
                    "department_name": "Karnataka State Audit Department",
                    "tagline": "AI Assisted Financial Audit Platform for Government Departments",
                    "state": "Karnataka",
                    "compliance_code": "KSAD-2024-AI",
                }),
                "general",
                True,
            ),
            (
                "demo_schemes",
                json.dumps([
                    "MGNREGA",
                    "PMAY-G",
                    "15th Finance Commission Grants",
                    "Jal Jeevan Mission",
                    "Swachh Bharat Mission (Gramin)",
                ]),
                "schemes",
                True,
            ),
        ]
        for key, val, cat, editable in settings_data:
            st = db.query(Setting).filter(Setting.key == key).first()
            if not st:
                st = Setting(key=key, value_json=val, category=cat, is_editable=editable)
                db.add(st)
                db.commit()
        print("[OK] System Settings seeded.")

        # 5. Seed Karnataka Holidays
        holidays_data = [
            (date(2024, 1, 15), "Makara Sankranti", "Karnataka", "Harvest and Sun transit festival"),
            (date(2024, 4, 9), "Ugadi", "Karnataka", "Kannada New Year"),
            (date(2024, 5, 1), "May Day", "Karnataka", "Labour Day"),
            (date(2024, 8, 15), "Independence Day", "Karnataka", "National Holiday"),
            (date(2024, 10, 2), "Gandhi Jayanti", "Karnataka", "Mahatma Gandhi Birthday"),
            (date(2024, 10, 12), "Ayudha Pooja / Vijaya Dashami", "Karnataka", "State festival of tools & victory"),
            (date(2024, 11, 1), "Kannada Rajyotsava", "Karnataka", "Karnataka State Formation Day"),
            (date(2025, 1, 26), "Republic Day", "Karnataka", "National Republic Day"),
        ]
        for hdate, hname, hstate, hdesc in holidays_data:
            h = db.query(Holiday).filter(Holiday.holiday_date == hdate, Holiday.name == hname).first()
            if not h:
                h = Holiday(holiday_date=hdate, name=hname, state=hstate, description=hdesc)
                db.add(h)
                db.commit()
        print("[OK] Karnataka Holidays seeded.")

        # 6. Seed Baseline Demo Audit Case for Mysuru ZP
        case = db.query(AuditCase).filter(AuditCase.case_number == "CAS-2024-MYS-001").first()
        if not case:
            case = AuditCase(
                case_number="CAS-2024-MYS-001",
                title="Annual Statutory Financial Audit: Mysuru Zilla Panchayat (FY 2024-25)",
                financial_year="2024-25",
                department_id=dept_map["ZP_MYS"].id,
                lead_auditor_id=user_map["senior.auditor@stateaudit.kar.gov.in"].id,
                status="in_progress",
                risk_level="medium",
                scope_notes="Statutory audit of MGNREGA muster rolls, 15th FC capital expenditures, and PMAY-G disbursements.",
            )
            db.add(case)
            db.commit()
            db.refresh(case)

        # 7. Genesis Audit Trail Entry
        log_activity(
            db=db,
            action="system:genesis",
            entity_type="system",
            entity_id="state_audit_genesis",
            actor_name="System Initializer",
            payload={"message": "STATE AUDIT AI Karnataka baseline seed initialized successfully."},
        )
        print("[OK] Genesis Audit Trail record created.")
        print("[DONE] Seeding Complete! All Phase 1 baseline entities created.")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] Error during seeding: {e}")
        raise e
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed()
