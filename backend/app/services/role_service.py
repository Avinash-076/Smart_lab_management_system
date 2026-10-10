from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.schemas.role_schema import (
    PermissionDefinition,
    RoleCreate,
    RolePermissionUpdateItem,
    RoleUpdate,
)

# Standard catalog of system permissions with metadata
AVAILABLE_PERMISSIONS: list[dict[str, str]] = [
    {
        "action_code": "VIEW_COMPUTERS",
        "name": "View Computers & Telemetry",
        "category": "Computers",
        "description": "View connected computers, live telemetry, hardware specs, processes, software, and usage sessions.",
    },
    {
        "action_code": "REGISTER_COMPUTER",
        "name": "Register Computers",
        "category": "Computers",
        "description": "Manually register and approve new computer nodes.",
    },
    {
        "action_code": "UPDATE_COMPUTER",
        "name": "Update Computers",
        "category": "Computers",
        "description": "Modify computer metadata, laboratory room assignment, and operating parameters.",
    },
    {
        "action_code": "DELETE_COMPUTER",
        "name": "Delete Computers",
        "category": "Computers",
        "description": "Decommission and remove computer nodes and telemetry records.",
    },
    {
        "action_code": "PROVISION_AGENT",
        "name": "Provision Client Agents",
        "category": "Security",
        "description": "Generate, rotate, and manage enrollment keys for client agent installations.",
    },
    {
        "action_code": "ISSUE_COMMAND",
        "name": "Issue Remote Commands",
        "category": "Operations",
        "description": "Execute remote operational commands including lock, message, restart, and shutdown.",
    },
    {
        "action_code": "MANAGE_USERS",
        "name": "Manage Users",
        "category": "Administration",
        "description": "Create, modify, activate, deactivate, and remove user accounts.",
    },
    {
        "action_code": "MANAGE_ROLES",
        "name": "Manage Roles & Permissions",
        "category": "Administration",
        "description": "Define roles and configure fine-grained access permission matrices.",
    },
    {
        "action_code": "MANAGE_ISSUES",
        "name": "Manage Issues",
        "category": "Operations",
        "description": "Create, assign, escalate, and resolve computer hardware and software issues.",
    },
    {
        "action_code": "MANAGE_MAINTENANCE",
        "name": "Manage Maintenance",
        "category": "Operations",
        "description": "Schedule, perform, and complete computer maintenance tasks.",
    },
    {
        "action_code": "MANAGE_SETTINGS",
        "name": "Manage System Settings",
        "category": "Administration",
        "description": "Configure laboratory metadata, telemetry thresholds, notification alerts, and client agent parameters.",
    },
]

KNOWN_ACTION_CODES = {p["action_code"] for p in AVAILABLE_PERMISSIONS}


def get_available_permissions() -> list[PermissionDefinition]:
    """Return all system permission definitions."""
    return [
        PermissionDefinition(**perm) for perm in AVAILABLE_PERMISSIONS
    ]


def get_roles(db: Session) -> list[dict]:
    """List all roles with their assigned permissions and user counts."""
    roles = db.scalars(
        select(Role).order_by(Role.id.asc())
    ).all()

    # Get user counts grouped by role_id
    user_counts_raw = db.execute(
        select(User.role_id, func.count(User.id)).group_by(User.role_id)
    ).all()
    user_counts = {role_id: count for role_id, count in user_counts_raw}

    results = []
    for role in roles:
        results.append({
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "user_count": user_counts.get(role.id, 0),
            "permissions": role.permissions,
        })
    return results


def get_role_by_id(db: Session, role_id: int) -> Role | None:
    """Retrieve a single role by ID with permissions eagerly loaded."""
    return db.scalar(
        select(Role)
        .where(Role.id == role_id)
        .options(joinedload(Role.permissions))
    )


def get_role_by_name(db: Session, name: str) -> Role | None:
    """Retrieve a single role by name."""
    return db.scalar(
        select(Role).where(Role.name == name)
    )


def get_role_user_count(db: Session, role_id: int) -> int:
    """Return number of users assigned to a role."""
    return int(
        db.scalar(
            select(func.count(User.id)).where(User.role_id == role_id)
        )
        or 0
    )


def create_role(db: Session, role_data: RoleCreate) -> Role:
    """Create a new role with optional initial permissions."""
    name = role_data.name.strip()
    if not name:
        raise ValueError("Role name cannot be empty")

    existing = get_role_by_name(db, name)
    if existing:
        raise ValueError("Role with this name already exists")

    description = (
        role_data.description.strip()
        if role_data.description
        else None
    )

    role = Role(name=name, description=description)
    try:
        db.add(role)
        db.commit()
        db.refresh(role)

        # Initialize permissions
        granted_codes = set(role_data.permissions or [])
        for perm in AVAILABLE_PERMISSIONS:
            code = perm["action_code"]
            is_allowed = code in granted_codes
            db.add(
                RolePermission(
                    role_id=role.id,
                    action_code=code,
                    allowed=is_allowed,
                )
            )
        db.commit()
        db.refresh(role)
        return role

    except IntegrityError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def update_role(
    db: Session,
    role: Role,
    role_data: RoleUpdate,
) -> Role:
    """Update role metadata (name, description)."""
    if role_data.name is not None:
        name = role_data.name.strip()
        if not name:
            raise ValueError("Role name cannot be empty")
        if role.name == "Administrator" and name != "Administrator":
            raise ValueError("Cannot rename the primary Administrator role")

        existing = db.scalar(
            select(Role).where(
                Role.name == name,
                Role.id != role.id,
            )
        )
        if existing:
            raise ValueError("Role with this name already exists")
        role.name = name

    if role_data.description is not None:
        role.description = role_data.description.strip() or None

    try:
        db.commit()
        db.refresh(role)
        return role
    except IntegrityError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def delete_role(db: Session, role: Role) -> None:
    """Delete a custom role if no users are currently assigned to it."""
    if role.name == "Administrator":
        raise ValueError("Cannot delete the primary Administrator role")

    user_count = get_role_user_count(db, role.id)
    if user_count > 0:
        raise ValueError(
            f"Cannot delete role '{role.name}' because {user_count} user(s) are assigned to it"
        )

    try:
        db.delete(role)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def update_role_permissions(
    db: Session,
    role: Role,
    permissions_items: list[RolePermissionUpdateItem],
) -> list[RolePermission]:
    """Update permissions for a given role with safety constraints for Administrator."""
    # Build a lookup of existing permissions for this role
    existing_perms = {
        p.action_code: p for p in role.permissions
    }

    for item in permissions_items:
        action_code = item.action_code.strip()
        if action_code not in KNOWN_ACTION_CODES:
            raise ValueError(f"Unknown permission action code: {action_code}")

        # Safety lock: Cannot revoke MANAGE_ROLES or MANAGE_USERS or VIEW_COMPUTERS from Administrator role
        if (
            role.name == "Administrator"
            and action_code in ("MANAGE_ROLES", "MANAGE_USERS", "VIEW_COMPUTERS")
            and not item.allowed
        ):
            raise ValueError(
                f"Cannot revoke critical permission '{action_code}' from Administrator role"
            )

        if action_code in existing_perms:
            existing_perms[action_code].allowed = item.allowed
        else:
            new_perm = RolePermission(
                role_id=role.id,
                action_code=action_code,
                allowed=item.allowed,
            )
            db.add(new_perm)

    try:
        db.commit()
        db.refresh(role)
        return role.permissions
    except IntegrityError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def seed_default_roles_and_permissions(db: Session) -> None:
    """Seed standard roles (Administrator, Lab Administrator, Technician, Operator) and their default permissions."""
    default_role_configs = [
        {
            "name": "Administrator",
            "description": "Full access to all SLMS features, remote operations, user management, and system settings.",
            "allowed_codes": list(KNOWN_ACTION_CODES),
        },
        {
            "name": "Lab Administrator",
            "description": "Manage laboratory computers, remote operations, issues, maintenance, and client provisioning.",
            "allowed_codes": [
                "VIEW_COMPUTERS",
                "REGISTER_COMPUTER",
                "UPDATE_COMPUTER",
                "PROVISION_AGENT",
                "ISSUE_COMMAND",
                "MANAGE_ISSUES",
                "MANAGE_MAINTENANCE",
            ],
        },
        {
            "name": "Technician",
            "description": "Monitor computer status, update configurations, and manage issue and maintenance records.",
            "allowed_codes": [
                "VIEW_COMPUTERS",
                "UPDATE_COMPUTER",
                "MANAGE_ISSUES",
                "MANAGE_MAINTENANCE",
            ],
        },
        {
            "name": "Operator",
            "description": "View laboratory computers and issue approved remote commands.",
            "allowed_codes": [
                "VIEW_COMPUTERS",
                "ISSUE_COMMAND",
            ],
        },
    ]

    for config in default_role_configs:
        role = get_role_by_name(db, config["name"])
        if not role:
            role = Role(
                name=config["name"],
                description=config["description"],
            )
            db.add(role)
            db.commit()
            db.refresh(role)

        existing_codes = {p.action_code for p in role.permissions}
        for code in KNOWN_ACTION_CODES:
            if code not in existing_codes:
                is_allowed = code in config["allowed_codes"]
                db.add(
                    RolePermission(
                        role_id=role.id,
                        action_code=code,
                        allowed=is_allowed,
                    )
                )
    db.commit()
