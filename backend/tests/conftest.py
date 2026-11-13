import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import limiter
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.seed.seed_data import seed

# Disable rate limiter during tests
limiter.enabled = False

# Use in-memory or dedicated test sqlite db
TEST_DB_URL = "sqlite:///./test_state_audit.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Configure test environment
    settings.DATABASE_URL = TEST_DB_URL
    from app.core.database import SessionLocal
    SessionLocal.configure(bind=test_engine)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Seed initial test data using test session
    init_session = TestingSessionLocal()
    from app.seed.full_seed import run_full_seed
    run_full_seed(init_session)
    init_session.close()

    yield

    # Teardown
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_state_audit.db"):
        try:
            os.remove("./test_state_audit.db")
        except Exception:
            pass


@pytest.fixture(scope="function")
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_tokens(client):
    """Returns valid JWT access tokens for each of the 4 demo roles."""
    roles = {
        "admin": ("admin@stateaudit.kar.gov.in", "AdminPassword@2024"),
        "officer": ("officer@stateaudit.kar.gov.in", "OfficerPassword@2024"),
        "senior_auditor": ("senior.auditor@stateaudit.kar.gov.in", "SeniorPassword@2024"),
        "auditor": ("auditor@stateaudit.kar.gov.in", "AuditorPassword@2024"),
    }
    tokens = {}
    for role_name, (email, password) in roles.items():
        res = client.post("/api/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200, f"Login failed for {role_name}: {res.text}"
        tokens[role_name] = res.json()["access_token"]
    return tokens
