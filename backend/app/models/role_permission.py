from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id"),
        nullable=False
    )

    action_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    allowed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )