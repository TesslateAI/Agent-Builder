from sqlalchemy import String, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, Dict
from .base import Base

class Organizations(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        Index("idx_organizations_name", "name"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    users = relationship("Users", back_populates="organization", cascade="all, delete-orphan")
    roles = relationship("Roles", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Projects", back_populates="organization", cascade="all, delete-orphan")