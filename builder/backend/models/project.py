from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional
from .base import Base

class Projects(Base): 
    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_projects_organization_id", "organization_id"),
        Index("idx_projects_owner_id", "owner_id"),
    )
    
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    flows = relationship("Flow", back_populates="project", cascade="all, delete-orphan")
    organization = relationship("Organizations", back_populates="projects")
    owner = relationship("Users", foreign_keys=[owner_id])