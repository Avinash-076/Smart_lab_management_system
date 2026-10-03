"""
Backend tests for SLMS User Authentication API (Phase 1).
Verifies:
- POST /api/auth/login (success, invalid password, non-existent user, payload validation)
- POST /api/auth/refresh (success, wrong token type, expired token, malformed token, non-existent user)
- Token payload structure and verification
- Protected endpoint behavior with valid, invalid, and missing user tokens
"""

from datetime import datetime, timedelta, timezone
import pytest
from jose import jwt

from app.auth import create_access_token, create_refresh_token, hash_password
from app.config import settings
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User


@pytest.fixture
def auth_user(db_session):
    """Create a test user with Administrator role and VIEW_COMPUTERS permission."""
    role = db_session.query(Role).filter_by(name="TestAdminRole").first()
    if not role:
        role = Role(name="TestAdminRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    perm = (
        db_session.query(RolePermission)
        .filter_by(role_id=role.id, action_code="VIEW_COMPUTERS")
        .first()
    )
    if not perm:
        perm = RolePermission(role_id=role.id, action_code="VIEW_COMPUTERS", allowed=True)
        db_session.add(perm)
        db_session.commit()

    user = db_session.query(User).filter_by(username="test_admin_user").first()
    if not user:
        user = User(
            username="test_admin_user",
            password_hash=hash_password("ValidPassword123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    return {
        "user_id": user.id,
        "username": "test_admin_user",
        "password": "ValidPassword123!",
        "role_id": role.id,
    }


def test_login_success(client, auth_user):
    """Test login with valid credentials returns access and refresh tokens."""
    payload = {
        "username": auth_user["username"],
        "password": auth_user["password"],
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Verify access token payload
    access_payload = jwt.decode(
        data["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert access_payload["sub"] == str(auth_user["user_id"])
    assert access_payload["type"] == "access"
    assert "exp" in access_payload

    # Verify refresh token payload
    refresh_payload = jwt.decode(
        data["refresh_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert refresh_payload["sub"] == str(auth_user["user_id"])
    assert refresh_payload["type"] == "refresh"
    assert "exp" in refresh_payload


def test_login_invalid_password(client, auth_user):
    """Test login with incorrect password returns 401 Unauthorized."""
    payload = {
        "username": auth_user["username"],
        "password": "WrongPassword!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_unknown_user(client):
    """Test login with non-existent username returns 401 Unauthorized."""
    payload = {
        "username": "non_existent_user_9999",
        "password": "SomePassword123!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_empty_fields_rejected(client):
    """Test login with empty strings fails pydantic schema validation."""
    response = client.post("/api/auth/login", json={"username": "", "password": ""})
    assert response.status_code == 422


def test_refresh_token_success(client, auth_user):
    """Test exchanging a valid refresh token for a new access token."""
    refresh_token = create_refresh_token({"sub": str(auth_user["user_id"])})
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Decode and verify the new access token
    access_payload = jwt.decode(
        data["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert access_payload["sub"] == str(auth_user["user_id"])
    assert access_payload["type"] == "access"


def test_refresh_with_access_token_rejected(client, auth_user):
    """Test providing an access token (type='access') to /refresh is rejected with 401."""
    access_token = create_access_token({"sub": str(auth_user["user_id"])})
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
    assert "Invalid token type" in response.json()["detail"]


def test_refresh_with_expired_token_rejected(client, auth_user):
    """Test providing an expired refresh token is rejected with 401."""
    expired_payload = {
        "sub": str(auth_user["user_id"]),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) - timedelta(days=1),
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": expired_token},
    )
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


def test_refresh_with_malformed_token_rejected(client):
    """Test providing a malformed token string returns 401."""
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "not.a.valid.jwt.token"},
    )
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


def test_refresh_for_deleted_user_rejected(client):
    """Test refresh token for a user ID that no longer exists returns 401."""
    token_for_missing_user = create_refresh_token({"sub": "99999999"})
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": token_for_missing_user},
    )
    assert response.status_code == 401
    assert "User no longer exists" in response.json()["detail"]


def test_protected_endpoint_without_token_rejected(client):
    """Test accessing protected route without Bearer token returns 401 or 403."""
    response = client.get("/api/clients")
    assert response.status_code in (401, 403)


def test_protected_endpoint_with_valid_user_token(client, auth_user):
    """Test accessing protected route with a valid user access token succeeds."""
    token = create_access_token({"sub": str(auth_user["user_id"])})
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/clients", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_protected_endpoint_with_expired_token_rejected(client, auth_user):
    """Test accessing protected route with an expired access token returns 401."""
    expired_payload = {
        "sub": str(auth_user["user_id"]),
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/clients", headers=headers)
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]
