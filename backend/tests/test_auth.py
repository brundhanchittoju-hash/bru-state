from datetime import timedelta
import pytest
from app.core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User


def test_argon2_hashing():
    raw = "KarnatakaAudit@2024"
    hashed = get_password_hash(raw)
    assert hashed != raw
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_issue_and_refresh(client):
    # Test valid login
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@stateaudit.kar.gov.in", "password": "AdminPassword@2024"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "admin@stateaudit.kar.gov.in"
    assert data["user"]["role"]["code"] == "administrator"

    # Test refresh token endpoint
    refresh_res = client.post(
        "/api/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert refresh_res.status_code == 200
    refreshed = refresh_res.json()
    assert "access_token" in refreshed

    # Test token expiry
    expired_token = create_access_token(
        subject="test_user",
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(ValueError, match="Token has expired"):
        decode_token(expired_token)


def test_account_lockout(client, db_session):
    email = "auditor@stateaudit.kar.gov.in"
    # Attempt 5 failed logins
    for _ in range(5):
        res = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword!"})
        assert res.status_code in (401, 403)

    # 6th attempt should return 403 Account Locked
    locked_res = client.post("/api/auth/login", json={"email": email, "password": "AuditorPassword@2024"})
    assert locked_res.status_code == 403
    assert "Account is temporarily locked" in locked_res.json()["detail"]

    # Reset lockout for following tests
    user = db_session.query(User).filter(User.email == email).first()
    if user:
        user.failed_login_attempts = 0
        user.locked_until = None
        db_session.commit()


def test_security_headers(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-xss-protection") == "1; mode=block"


def test_validation_errors(client):
    # Invalid email format
    res = client.post("/api/auth/login", json={"email": "not-an-email", "password": "pwd"})
    assert res.status_code == 422
    assert "detail" in res.json()

    # Missing password
    res2 = client.post("/api/auth/login", json={"email": "admin@stateaudit.kar.gov.in"})
    assert res2.status_code == 422
