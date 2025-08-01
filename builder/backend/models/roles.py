from sqlalchemy import String, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, List
from .base import Base

class Roles(Base):
    __tablename__ = "roles"
    __table_args__ = (
        Index("idx_roles_organization_id", "organization_id"),
        Index("idx_roles_name_org", "name", "organization_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permissions: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    organization_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )

    organization = relationship("Organizations", back_populates="roles")