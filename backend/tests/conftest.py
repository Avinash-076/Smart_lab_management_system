import os
import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure required environment variables for test execution
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-purposes-123456789")
os.environ.setdefault("DATABASE_URL", "sqlite:///test_slms.db")

from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, SessionLocal, engine
from app.models.computer import Computer
from app.models.agent_credential import AgentCredential
from app.auth import create_agent_access_token


@pytest.fixture(scope="session", autouse=True)
def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    for p in [Path("test_slms.db"), BACKEND_DIR / "test_slms.db"]:
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def registered_agent(db_session):
    # Ensure test computer and credential exist
    computer = db_session.get(Computer, 9999)
    if not computer:
        computer = Computer(
            id=9999,
            hostname="TEST-PC-9999",
            ip_address="192.168.1.99",
            mac_address="AA:BB:CC:DD:EE:FF",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(computer)
        db_session.commit()
        db_session.refresh(computer)

    credential = db_session.query(AgentCredential).filter_by(agent_id="test-agent-9999").first()
    if not credential:
        credential = AgentCredential(
            agent_id="test-agent-9999",
            secret_hash="fake-hash-12345",
            computer_id=computer.id,
            is_active=True,
        )
        db_session.add(credential)
        db_session.commit()
        db_session.refresh(credential)

    token = create_agent_access_token({
        "sub": credential.agent_id,
        "computer_id": computer.id,
    })

    return {
        "computer_id": computer.id,
        "agent_id": credential.agent_id,
        "token": token,
    }


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
