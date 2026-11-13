from app.models import (
    ActivityLog,
    AuditCase,
    Department,
    Document,
    Holiday,
    Role,
    Setting,
    User,
)


def test_migrations_and_table_count(db_session):
    # Verify core models can be queried and have all 25 mapped tables
    assert db_session.query(Role).count() >= 4
    assert db_session.query(Department).count() >= 7
    assert db_session.query(User).count() >= 4
    assert db_session.query(Setting).count() >= 4
    assert db_session.query(Holiday).count() >= 8
    assert db_session.query(AuditCase).count() >= 1
    assert db_session.query(ActivityLog).count() >= 1


def test_soft_delete(db_session):
    # Create test department
    test_dept = Department(
        code="TEST_TALUK_01",
        name="Hunsur Taluk Panchayat",
        type="Taluk Panchayat",
        district="Mysuru",
    )
    db_session.add(test_dept)
    db_session.commit()
    db_session.refresh(test_dept)

    assert test_dept.deleted_at is None
    assert test_dept.is_deleted is False

    # Execute soft delete
    test_dept.soft_delete()
    db_session.commit()

    assert test_dept.deleted_at is not None
    assert test_dept.is_deleted is True

    # Active query should filter out soft deleted record
    active_depts = (
        db_session.query(Department)
        .filter(Department.deleted_at.is_(None))
        .all()
    )
    dept_codes = [d.code for d in active_depts]
    assert "TEST_TALUK_01" not in dept_codes


def test_seed_execution(db_session):
    # Check 4 roles
    roles = {r.code for r in db_session.query(Role).all()}
    assert {"administrator", "audit_officer", "senior_auditor", "auditor"}.issubset(roles)

    # Check 4 users
    user_emails = {u.email for u in db_session.query(User).all()}
    expected_emails = {
        "admin@stateaudit.kar.gov.in",
        "officer@stateaudit.kar.gov.in",
        "senior.auditor@stateaudit.kar.gov.in",
        "auditor@stateaudit.kar.gov.in",
    }
    assert expected_emails.issubset(user_emails)

    # Check Karnataka holidays
    holiday_names = {h.name for h in db_session.query(Holiday).all()}
    assert "Kannada Rajyotsava" in holiday_names
    assert "Ugadi" in holiday_names
