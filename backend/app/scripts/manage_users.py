"""
Production User Management CLI Script.
Provides administrative actions for managing user accounts in compliance with statutory audit standards:
- set-password <email>: Prompts for hidden password input (never CLI argument) and enforces password policy.
- deactivate <email>: Soft-deactivates a user account (never hard-deletes) and logs hash-chained audit trail.
- deactivate-demo-users: Soft-deactivates all accounts flagged as demo, writing hash-chained audit entries.
- create-admin <email>: Prompts for hidden password input, validates policy, creates admin with audit trail.

All actions write to the hash-chained audit trail via existing services and NEVER hard-delete.
"""

import argparse
import getpass
import os
import re
import sys
from typing import List, Optional

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal
from app.core.security import validate_password_policy
from app.models.user import Department, Role, User
from app.schemas.user import UserCreate
from app.services.user_service import UserService

# Seeded demo emails recognized across all environments
KNOWN_DEMO_EMAILS = {
    "admin@stateaudit.kar.gov.in",
    "officer@stateaudit.kar.gov.in",
    "senior.auditor@stateaudit.kar.gov.in",
    "auditor@stateaudit.kar.gov.in",
    "auditor2@stateaudit.kar.gov.in",
    "auditor3@stateaudit.kar.gov.in",
    "priya.nair@stateaudit.kar.gov.in",
    "kavita.patil@stateaudit.kar.gov.in",
}


def is_demo_user(user: User) -> bool:
    """
    Identifies if a user account is flagged as demo:
    1. Direct is_demo attribute/column if present.
    2. Known demo seed emails.
    3. Seed demo full names containing role identifiers.
    """
    if getattr(user, "is_demo", False) is True:
        return True
    if user.email and user.email.lower().strip() in KNOWN_DEMO_EMAILS:
        return True
    if user.full_name and any(tag in user.full_name for tag in ["(Admin)", "(Audit Officer)", "(Senior Auditor)", "(Auditor)"]):
        return True
    return False


def get_session(db_url: Optional[str] = None) -> Session:
    """Returns database session (supports override for testing)."""
    if db_url:
        engine = create_engine(db_url)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return TestSession()
    return SessionLocal()


def action_set_password(email: str, db: Session) -> int:
    """Sets a user's password prompting with hidden input."""
    clean_email = email.lower().strip()
    user = (
        db.query(User)
        .filter(User.email == clean_email, User.deleted_at.is_(None))
        .first()
    )
    if not user:
        print(f"[ERROR] User with email '{clean_email}' not found.")
        return 1

    print(f"Setting password for user: {user.email} ({user.full_name})")
    pwd1 = getpass.getpass("Enter new password (hidden): ")
    pwd2 = getpass.getpass("Confirm new password (hidden): ")

    if pwd1 != pwd2:
        print("[ERROR] Passwords do not match.")
        return 1

    try:
        validate_password_policy(pwd1)
    except ValueError as e:
        print(f"[ERROR] Password policy violation: {e}")
        return 1

    try:
        UserService.set_user_password(
            db=db,
            user_id=user.id,
            new_password=pwd1,
            actor_name="CLI:manage_users",
        )
        print(f"[SUCCESS] Password successfully updated for user '{user.email}'.")
        print("  - Argon2id hash computed and stored.")
        print("  - Password policy verified (min 12 chars, mixed character types).")
        print("  - Hash-chained audit trail recorded.")
        return 0
    except Exception as exc:
        print(f"[ERROR] Failed to update password: {exc}")
        return 1


def action_deactivate(email: str, db: Session) -> int:
    """Soft-deactivates a user account."""
    clean_email = email.lower().strip()
    user = (
        db.query(User)
        .filter(User.email == clean_email, User.deleted_at.is_(None))
        .first()
    )
    if not user:
        print(f"[ERROR] User with email '{clean_email}' not found.")
        return 1

    if not user.is_active:
        print(f"[INFO] User '{user.email}' is already inactive. No changes made.")
        return 0

    try:
        UserService.deactivate_user(
            db=db,
            user_id=user.id,
            actor_name="CLI:manage_users",
        )
        print(f"[SUCCESS] User '{user.email}' ({user.full_name}) successfully deactivated.")
        print("  - Account status set to inactive (soft deactivation; not hard deleted).")
        print("  - Hash-chained audit trail recorded.")
        return 0
    except Exception as exc:
        print(f"[ERROR] Failed to deactivate user: {exc}")
        return 1


def action_deactivate_demo_users(db: Session) -> int:
    """Soft-deactivates all accounts flagged as demo."""
    all_users: List[User] = (
        db.query(User)
        .filter(User.deleted_at.is_(None))
        .all()
    )

    demo_users = [u for u in all_users if is_demo_user(u)]
    if not demo_users:
        print("[INFO] No demo user accounts found in the database.")
        return 0

    deactivated_count = 0
    already_inactive_count = 0

    print(f"Scanning for demo accounts ({len(demo_users)} detected)...")
    for u in demo_users:
        if not u.is_active:
            already_inactive_count += 1
            print(f"  • [ALREADY INACTIVE] {u.email} ({u.full_name})")
            continue

        try:
            UserService.deactivate_user(
                db=db,
                user_id=u.id,
                actor_name="CLI:manage_users",
            )
            deactivated_count += 1
            print(f"  • [DEACTIVATED] {u.email} ({u.full_name})")
        except Exception as exc:
            print(f"  • [ERROR] Could not deactivate {u.email}: {exc}")

    print("\n" + "=" * 60)
    print("DEMO USERS DEACTIVATION SUMMARY")
    print(f"  Demo accounts identified: {len(demo_users)}")
    print(f"  Accounts deactivated:     {deactivated_count}")
    print(f"  Previously inactive:      {already_inactive_count}")
    print("  Hash-chained audit trail entries appended for each deactivation.")
    print("  Zero records hard-deleted.")
    print("=" * 60)
    return 0


def action_create_admin(email: str, full_name: Optional[str], db: Session) -> int:
    """Creates a new production administrator account."""
    clean_email = email.lower().strip()

    # Basic email format check
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
        print(f"[ERROR] '{clean_email}' is not a valid email address.")
        return 1

    existing = (
        db.query(User)
        .filter(User.email == clean_email, User.deleted_at.is_(None))
        .first()
    )
    if existing:
        print(f"[ERROR] A user with email '{clean_email}' already exists.")
        return 1

    # Locate administrator role
    admin_role = (
        db.query(Role)
        .filter(Role.code == "administrator", Role.deleted_at.is_(None))
        .first()
    )
    if not admin_role:
        print("[ERROR] Role 'administrator' not found in database. Please ensure roles are seeded.")
        return 1

    # Locate default headquarters department if available
    dept = (
        db.query(Department)
        .filter(Department.code == "KSAD_HQ", Department.deleted_at.is_(None))
        .first()
    )

    if not full_name:
        try:
            prompt_name = input("Enter administrator full name [System Administrator]: ").strip()
            full_name = prompt_name or "System Administrator"
        except (EOFError, KeyboardInterrupt):
            full_name = "System Administrator"

    print(f"Creating administrator account: {clean_email} ({full_name})")
    pwd1 = getpass.getpass("Enter administrator password (hidden): ")
    pwd2 = getpass.getpass("Confirm administrator password (hidden): ")

    if pwd1 != pwd2:
        print("[ERROR] Passwords do not match.")
        return 1

    try:
        validate_password_policy(pwd1)
    except ValueError as e:
        print(f"[ERROR] Password policy violation: {e}")
        return 1

    try:
        user_in = UserCreate(
            email=clean_email,
            password=pwd1,
            full_name=full_name,
            role_id=admin_role.id,
            department_id=dept.id if dept else None,
            is_active=True,
        )
        new_admin = UserService.create_user(
            db=db,
            user_in=user_in,
            actor_name="CLI:manage_users",
        )
        print(f"\n[SUCCESS] Administrator account '{new_admin.email}' created successfully.")
        print(f"  - User ID:      {new_admin.id}")
        print(f"  - Full Name:    {new_admin.full_name}")
        print(f"  - Role:         {admin_role.name} ({admin_role.code})")
        print("  - Password:     Hashed with Argon2id and verified against complexity policy.")
        print("  - Audit Trail:  Immutable cryptographic hash-chained event recorded.")
        return 0
    except Exception as exc:
        print(f"[ERROR] Failed to create administrator account: {exc}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Production User Account Management CLI for State Audit AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.scripts.manage_users set-password user@domain.gov.in
  python -m app.scripts.manage_users deactivate old.auditor@domain.gov.in
  python -m app.scripts.manage_users deactivate-demo-users
  python -m app.scripts.manage_users create-admin admin@domain.gov.in --full-name "Chief Auditor"
        """,
    )
    parser.add_argument("--db-url", type=str, default=None, help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(dest="action", required=True, help="Administrative action to perform")

    # 1. set-password
    sp_set_pwd = subparsers.add_parser("set-password", help="Update password for a user (prompts for hidden input)")
    sp_set_pwd.add_argument("email", type=str, help="Email address of the user account")

    # 2. deactivate
    sp_deact = subparsers.add_parser("deactivate", help="Soft-deactivate a user account (never hard-deletes)")
    sp_deact.add_argument("email", type=str, help="Email address of the user account")

    # 3. deactivate-demo-users
    subparsers.add_parser("deactivate-demo-users", help="Soft-deactivate all demo accounts flagged in the system")

    # 4. create-admin
    sp_admin = subparsers.add_parser("create-admin", help="Create a new administrator account (prompts for hidden password)")
    sp_admin.add_argument("email", type=str, help="Email address for the administrator")
    sp_admin.add_argument("--full-name", type=str, default=None, help="Full name of the administrator")

    args = parser.parse_args()

    db = get_session(args.db_url)
    try:
        if args.action == "set-password":
            return action_set_password(args.email, db)
        elif args.action == "deactivate":
            return action_deactivate(args.email, db)
        elif args.action == "deactivate-demo-users":
            return action_deactivate_demo_users(db)
        elif args.action == "create-admin":
            return action_create_admin(args.email, args.full_name, db)
        else:
            parser.print_help()
            return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

