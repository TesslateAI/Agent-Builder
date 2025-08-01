from sqlalchemy import Integer, String, ForeignKey, Index, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional
from .base import Base

class UserProjectRoles(Base):
    __tablename__ = "user_project_roles"
    __table_args__ = (
        Index("idx_user_project_roles_user_id", "user_id"),
        Index("idx_user_project_roles_project_id", "project_id"),
        Index("idx_user_project_roles_role_id", "role_id"),
        Index("idx_user_project_roles_unique", "user_id", "project_id", "role_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    assigned_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"), nullable=True)