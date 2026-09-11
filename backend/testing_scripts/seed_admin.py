from app.database import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.auth import hash_password

db = SessionLocal()

role = db.query(Role).filter(Role.name == "Administrator").first()
if role is None:
    role = Role(name="Administrator")
    db.add(role)
    db.commit()
    db.refresh(role)

existing_user = db.query(User).filter(User.username == "admin").first()
if existing_user is None:
    user = User(
        username="admin",
        password_hash=hash_password("testpassword123"),
        role_id=role.id,
    )
    db.add(user)
    db.commit()
    print(f"Created user 'admin' with role '{role.name}'")
else:
    print("User 'admin' already exists — skipping.")

# Seed permissions for Administrator — full access to computer management
action_codes = [
    "VIEW_COMPUTERS",
    "REGISTER_COMPUTER",
    "UPDATE_COMPUTER",
    "DELETE_COMPUTER",
    "PROVISION_AGENT",
    "ISSUE_COMMAND"
]

for code in action_codes:
    existing_permission = (
        db.query(RolePermission)
        .filter(
            RolePermission.role_id == role.id,
            RolePermission.action_code == code,
        )
        .first()
    )
    if existing_permission is None:
        db.add(RolePermission(role_id=role.id, action_code=code, allowed=True))
        print(f"Added permission '{code}' for role '{role.name}'")

db.commit()
db.close()