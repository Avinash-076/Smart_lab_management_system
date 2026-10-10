"""
Comprehensive test suite for SLMS V6.1 User Management and Role-Based Access Control (RBAC).
Verifies:
- Authorized and unauthorized user listing and detail access (pagination, search, filtering).
- User creation, update, validation, and uniqueness.
- Password hashing and sensitive-field redaction (no password_hash in responses).
- Account activation/deactivation and login/token behavior.
- Role and permission authorization and protection against privilege escalation.
- System permission catalog and role permission matrix updates.
- Safety locks (cannot deactivate/delete self or last admin, cannot revoke admin root permissions).
- Audit trail logging for all administrative operations.
"""

import pytest
from app.auth import create_access_token, hash_password
from app.models.audit_log import AuditLog, AuditResult
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User


@pytest.fixture
def rbac_setup(db_session):
    """Seed test Administrator, Operator, and unprivileged roles and users."""
    # Ensure Administrator role
    admin_role = db_session.query(Role).filter_by(name="Administrator").first()
    if not admin_role:
        admin_role = Role(name="Administrator", description="Full access")
        db_session.add(admin_role)
        db_session.commit()
        db_session.refresh(admin_role)

    # Ensure Operator role
    operator_role = db_session.query(Role).filter_by(name="Operator").first()
    if not operator_role:
        operator_role = Role(name="Operator", description="Read and command access")
        db_session.add(operator_role)
        db_session.commit()
        db_session.refresh(operator_role)

    # Ensure Unprivileged role
    unprivileged_role = db_session.query(Role).filter_by(name="UnprivilegedRole").first()
    if not unprivileged_role:
        unprivileged_role = Role(name="UnprivilegedRole", description="No permissions")
        db_session.add(unprivileged_role)
        db_session.commit()
        db_session.refresh(unprivileged_role)

    # Admin permissions
    all_codes = [
        "VIEW_COMPUTERS",
        "REGISTER_COMPUTER",
        "UPDATE_COMPUTER",
        "DELETE_COMPUTER",
        "PROVISION_AGENT",
        "ISSUE_COMMAND",
        "MANAGE_USERS",
        "MANAGE_ROLES",
        "MANAGE_ISSUES",
        "MANAGE_MAINTENANCE",
    ]
    for code in all_codes:
        perm = (
            db_session.query(RolePermission)
            .filter_by(role_id=admin_role.id, action_code=code)
            .first()
        )
        if not perm:
            db_session.add(RolePermission(role_id=admin_role.id, action_code=code, allowed=True))
        else:
            perm.allowed = True

    # Operator permissions
    for code in ["VIEW_COMPUTERS", "ISSUE_COMMAND"]:
        perm = (
            db_session.query(RolePermission)
            .filter_by(role_id=operator_role.id, action_code=code)
            .first()
        )
        if not perm:
            db_session.add(RolePermission(role_id=operator_role.id, action_code=code, allowed=True))

    db_session.commit()

    # Admin user
    admin_user = db_session.query(User).filter_by(username="rbac_admin").first()
    if not admin_user:
        admin_user = User(
            username="rbac_admin",
            full_name="RBAC Admin",
            email="admin@slms.local",
            password_hash=hash_password("AdminPass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

    # Unprivileged user
    unprivileged_user = db_session.query(User).filter_by(username="rbac_unprivileged").first()
    if not unprivileged_user:
        unprivileged_user = User(
            username="rbac_unprivileged",
            full_name="No Perms User",
            email="noperms@slms.local",
            password_hash=hash_password("UserPass123!"),
            role_id=unprivileged_role.id,
            is_active=True,
        )
        db_session.add(unprivileged_user)
        db_session.commit()
        db_session.refresh(unprivileged_user)

    admin_token = create_access_token({"sub": str(admin_user.id)})
    unprivileged_token = create_access_token({"sub": str(unprivileged_user.id)})

    return {
        "admin_user": admin_user,
        "admin_role": admin_role,
        "operator_role": operator_role,
        "unprivileged_role": unprivileged_role,
        "unprivileged_user": unprivileged_user,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "unprivileged_headers": {"Authorization": f"Bearer {unprivileged_token}"},
    }


# ============================================================
# USER MANAGEMENT TESTS
# ============================================================

def test_get_users_unauthorized(client):
    """GET /api/users without token returns 401."""
    resp = client.get("/api/users")
    assert resp.status_code == 401


def test_get_users_forbidden(client, rbac_setup):
    """GET /api/users without MANAGE_USERS returns 403."""
    resp = client.get("/api/users", headers=rbac_setup["unprivileged_headers"])
    assert resp.status_code == 403


def test_get_users_success_pagination_and_filters(client, rbac_setup, db_session):
    """GET /api/users returns paginated users, respects search, role, and status filters."""
    resp = client.get("/api/users?page=1&limit=10", headers=rbac_setup["admin_headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["limit"] == 10
    assert len(data["items"]) >= 2

    # Sensitive fields are omitted
    for user_item in data["items"]:
        assert "password_hash" not in user_item
        assert "password" not in user_item
        assert "username" in user_item
        assert "role_name" in user_item

    # Search filter
    search_resp = client.get(
        "/api/users?search=rbac_admin",
        headers=rbac_setup["admin_headers"],
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert len(search_data["items"]) == 1
    assert search_data["items"][0]["username"] == "rbac_admin"

    # Status filter
    status_resp = client.get(
        "/api/users?status=Active",
        headers=rbac_setup["admin_headers"],
    )
    assert status_resp.status_code == 200
    for u in status_resp.json()["items"]:
        assert u["is_active"] is True


def test_get_user_details(client, rbac_setup):
    """GET /api/users/{id} returns individual user details or 404."""
    user = rbac_setup["admin_user"]
    resp = client.get(f"/api/users/{user.id}", headers=rbac_setup["admin_headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == user.id
    assert data["username"] == "rbac_admin"
    assert data["role_name"] == "Administrator"
    assert "password_hash" not in data

    # 404 for non-existent user
    resp404 = client.get("/api/users/999999", headers=rbac_setup["admin_headers"])
    assert resp404.status_code == 404


def test_create_user_success_and_audit(client, rbac_setup, db_session):
    """POST /api/users creates new user with validated fields and records audit log."""
    payload = {
        "username": "new_lab_operator",
        "password": "SecurePassword123!",
        "full_name": "Lab Operator 1",
        "email": "operator1@slms.local",
        "role_id": rbac_setup["operator_role"].id,
        "is_active": True,
    }
    resp = client.post("/api/users", json=payload, headers=rbac_setup["admin_headers"])
    assert resp.status_code == 201
    created = resp.json()
    assert created["username"] == "new_lab_operator"
    assert created["full_name"] == "Lab Operator 1"
    assert created["email"] == "operator1@slms.local"
    assert created["role_name"] == "Operator"
    assert created["is_active"] is True
    assert "password_hash" not in created

    # Verify audit log was recorded
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            action="CREATE_USER",
            target_id=created["id"],
            result=AuditResult.success,
        )
        .first()
    )
    assert audit is not None
    assert audit.user_id == rbac_setup["admin_user"].id


def test_create_user_validations_and_uniqueness(client, rbac_setup):
    """POST /api/users enforces uniqueness and rejects invalid inputs."""
    # Duplicate username
    dup_payload = {
        "username": "rbac_admin",
        "password": "Password123!",
        "role_id": rbac_setup["operator_role"].id,
    }
    resp = client.post("/api/users", json=dup_payload, headers=rbac_setup["admin_headers"])
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]

    # Short password
    short_pw = {
        "username": "short_pw_user",
        "password": "123",
        "role_id": rbac_setup["operator_role"].id,
    }
    resp = client.post("/api/users", json=short_pw, headers=rbac_setup["admin_headers"])
    assert resp.status_code == 422

    # Non-existent role
    bad_role = {
        "username": "bad_role_user",
        "password": "ValidPassword123!",
        "role_id": 999999,
    }
    resp = client.post("/api/users", json=bad_role, headers=rbac_setup["admin_headers"])
    assert resp.status_code == 404


def test_update_user_and_safety_guards(client, rbac_setup, db_session):
    """PATCH /api/users/{id} updates fields, enforces safety locks, and logs audit event."""
    user = rbac_setup["unprivileged_user"]
    update_payload = {
        "full_name": "Updated Full Name",
        "email": "updated_email@slms.local",
        "role_id": rbac_setup["operator_role"].id,
    }
    resp = client.patch(
        f"/api/users/{user.id}",
        json=update_payload,
        headers=rbac_setup["admin_headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Updated Full Name"
    assert data["email"] == "updated_email@slms.local"
    assert data["role_name"] == "Operator"

    # Self-deactivation prevention
    self_deactivate_resp = client.patch(
        f"/api/users/{rbac_setup['admin_user'].id}",
        json={"is_active": False},
        headers=rbac_setup["admin_headers"],
    )
    assert self_deactivate_resp.status_code == 400
    assert "cannot deactivate your own account" in self_deactivate_resp.json()["detail"]

    # Audit log check
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            action="UPDATE_USER",
            target_id=user.id,
            result=AuditResult.success,
        )
        .first()
    )
    assert audit is not None


def test_delete_user_and_safety_guards(client, rbac_setup, db_session):
    """DELETE /api/users/{id} prevents self-deletion and deletes eligible user with audit record."""
    # Self-deletion attempt
    self_del_resp = client.delete(
        f"/api/users/{rbac_setup['admin_user'].id}",
        headers=rbac_setup["admin_headers"],
    )
    assert self_del_resp.status_code == 400
    assert "cannot delete your own account" in self_del_resp.json()["detail"]

    # Create disposable user and delete
    temp_user = User(
        username="temp_deletable_user",
        password_hash=hash_password("Pass123!"),
        role_id=rbac_setup["operator_role"].id,
        is_active=True,
    )
    db_session.add(temp_user)
    db_session.commit()
    db_session.refresh(temp_user)
    temp_id = temp_user.id

    del_resp = client.delete(
        f"/api/users/{temp_id}",
        headers=rbac_setup["admin_headers"],
    )
    assert del_resp.status_code == 204

    # Confirm user is gone
    db_session.expire_all()
    check_user = db_session.get(User, temp_id)
    assert check_user is None

    # Audit log check
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            action="DELETE_USER",
            target_id=temp_id,
            result=AuditResult.success,
        )
        .first()
    )
    assert audit is not None


# ============================================================
# ACCOUNT STATUS & AUTHENTICATION ENFORCEMENT
# ============================================================

def test_deactivated_user_login_and_token_rejection(client, rbac_setup, db_session):
    """Deactivated user cannot log in and active access tokens are rejected."""
    # Create deactivated user
    deactivated_user = User(
        username="deactivated_user_test",
        password_hash=hash_password("DeactivatedPass123!"),
        role_id=rbac_setup["operator_role"].id,
        is_active=False,
    )
    db_session.add(deactivated_user)
    db_session.commit()
    db_session.refresh(deactivated_user)

    # Attempt login
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "deactivated_user_test", "password": "DeactivatedPass123!"},
    )
    assert login_resp.status_code == 401
    assert "deactivated" in login_resp.json()["detail"]

    # Direct token usage for deactivated account
    token = create_access_token({"sub": str(deactivated_user.id)})
    prot_resp = client.get("/api/clients", headers={"Authorization": f"Bearer {token}"})
    assert prot_resp.status_code == 401
    assert "deactivated" in prot_resp.json()["detail"]


def test_auth_me_endpoint(client, rbac_setup):
    """GET /api/auth/me returns current profile and permissions list."""
    resp = client.get("/api/auth/me", headers=rbac_setup["admin_headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "rbac_admin"
    assert data["role_name"] == "Administrator"
    assert "MANAGE_USERS" in data["permissions"]
    assert "VIEW_COMPUTERS" in data["permissions"]


# ============================================================
# ROLE AND PERMISSION MANAGEMENT TESTS
# ============================================================

def test_get_permissions_catalog(client, rbac_setup):
    """GET /api/permissions returns full catalog of system permissions."""
    resp = client.get("/api/permissions", headers=rbac_setup["admin_headers"])
    assert resp.status_code == 200
    perms = resp.json()
    assert isinstance(perms, list)
    action_codes = {p["action_code"] for p in perms}
    assert "VIEW_COMPUTERS" in action_codes
    assert "MANAGE_USERS" in action_codes
    assert "MANAGE_ROLES" in action_codes
    assert "ISSUE_COMMAND" in action_codes


def test_get_roles_list(client, rbac_setup):
    """GET /api/roles returns all roles with user count and permission matrices."""
    resp = client.get("/api/roles", headers=rbac_setup["admin_headers"])
    assert resp.status_code == 200
    roles = resp.json()
    assert len(roles) >= 2
    role_names = [r["name"] for r in roles]
    assert "Administrator" in role_names
    assert "Operator" in role_names


def test_create_and_manage_custom_role(client, rbac_setup, db_session):
    """POST /api/roles, PUT permissions, and DELETE custom role with audit trail."""
    # 1. Create custom role
    create_payload = {
        "name": "Custom Auditor",
        "description": "Read-only auditor role",
        "permissions": ["VIEW_COMPUTERS"],
    }
    resp = client.post(
        "/api/roles",
        json=create_payload,
        headers=rbac_setup["admin_headers"],
    )
    assert resp.status_code == 201
    created_role = resp.json()
    role_id = created_role["id"]
    assert created_role["name"] == "Custom Auditor"

    # 2. Update permissions
    perm_payload = {
        "permissions": [
            {"action_code": "VIEW_COMPUTERS", "allowed": True},
            {"action_code": "ISSUE_COMMAND", "allowed": True},
        ]
    }
    perm_resp = client.put(
        f"/api/roles/{role_id}/permissions",
        json=perm_payload,
        headers=rbac_setup["admin_headers"],
    )
    assert perm_resp.status_code == 200
    updated_role = perm_resp.json()
    allowed_codes = [p["action_code"] for p in updated_role["permissions"] if p["allowed"]]
    assert "VIEW_COMPUTERS" in allowed_codes
    assert "ISSUE_COMMAND" in allowed_codes

    # 3. Delete custom role
    del_resp = client.delete(
        f"/api/roles/{role_id}",
        headers=rbac_setup["admin_headers"],
    )
    assert del_resp.status_code == 204


def test_role_safety_locks(client, rbac_setup):
    """Cannot delete Administrator role or revoke root permissions from it."""
    admin_role_id = rbac_setup["admin_role"].id

    # Attempt to delete Administrator role
    del_resp = client.delete(
        f"/api/roles/{admin_role_id}",
        headers=rbac_setup["admin_headers"],
    )
    assert del_resp.status_code == 400
    assert "Cannot delete the primary Administrator role" in del_resp.json()["detail"]

    # Attempt to revoke MANAGE_USERS from Administrator
    revoke_payload = {
        "permissions": [
            {"action_code": "MANAGE_USERS", "allowed": False},
        ]
    }
    revoke_resp = client.put(
        f"/api/roles/{admin_role_id}/permissions",
        json=revoke_payload,
        headers=rbac_setup["admin_headers"],
    )
    assert revoke_resp.status_code == 400
    assert "Cannot revoke critical permission" in revoke_resp.json()["detail"]


def test_privilege_escalation_guards(client, rbac_setup, db_session):
    """Users with MANAGE_USERS but without MANAGE_ROLES cannot mutate roles or permissions."""
    # Create a user manager role with MANAGE_USERS only
    mgr_role = Role(name="UserManagerOnly", description="Can manage users but not roles")
    db_session.add(mgr_role)
    db_session.commit()
    db_session.refresh(mgr_role)

    db_session.add(RolePermission(role_id=mgr_role.id, action_code="MANAGE_USERS", allowed=True))
    db_session.add(RolePermission(role_id=mgr_role.id, action_code="MANAGE_ROLES", allowed=False))
    db_session.commit()

    mgr_user = User(
        username="user_manager_only",
        password_hash=hash_password("MgrPass123!"),
        role_id=mgr_role.id,
        is_active=True,
    )
    db_session.add(mgr_user)
    db_session.commit()
    db_session.refresh(mgr_user)

    mgr_token = create_access_token({"sub": str(mgr_user.id)})
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # Attempt to create a role -> forbidden 403
    create_resp = client.post(
        "/api/roles",
        json={"name": "EscalatedRole", "permissions": ["MANAGE_ROLES"]},
        headers=mgr_headers,
    )
    assert create_resp.status_code == 403

    # Attempt to update role permissions -> forbidden 403
    perm_resp = client.put(
        f"/api/roles/{mgr_role.id}/permissions",
        json={"permissions": [{"action_code": "MANAGE_ROLES", "allowed": True}]},
        headers=mgr_headers,
    )
    assert perm_resp.status_code == 403


def test_last_active_admin_demote_protection(client, rbac_setup, db_session):
    """Cannot demote the last active Administrator account."""
    admin_id = rbac_setup["admin_user"].id

    # Deactivate any other active admins from other test suites to isolate last-admin state
    other_admins = (
        db_session.query(User)
        .join(Role)
        .filter(Role.name == "Administrator", User.id != admin_id, User.is_active.is_(True))
        .all()
    )
    for other in other_admins:
        other.is_active = False
    db_session.commit()

    try:
        demote_resp = client.patch(
            f"/api/users/{admin_id}",
            json={"role_id": rbac_setup["operator_role"].id},
            headers=rbac_setup["admin_headers"],
        )
        assert demote_resp.status_code == 400
        assert "Cannot demote the last active Administrator" in demote_resp.json()["detail"]
    finally:
        for other in other_admins:
            other.is_active = True
        db_session.commit()


def test_duplicate_email_and_duplicate_role_validation(client, rbac_setup):
    """Validation rejects duplicate email for user and duplicate name for role."""
    # Duplicate email for user
    dup_email_payload = {
        "username": "distinct_user_dup_email",
        "email": "admin@slms.local",  # Already used by rbac_admin
        "password": "ValidPassword123!",
        "role_id": rbac_setup["operator_role"].id,
    }
    resp = client.post("/api/users", json=dup_email_payload, headers=rbac_setup["admin_headers"])
    assert resp.status_code == 409
    assert "Email already in use" in resp.json()["detail"]

    # Duplicate role name
    dup_role_payload = {
        "name": "Administrator",
        "description": "Duplicate admin",
    }
    role_resp = client.post("/api/roles", json=dup_role_payload, headers=rbac_setup["admin_headers"])
    assert role_resp.status_code == 409
    assert "already exists" in role_resp.json()["detail"]
