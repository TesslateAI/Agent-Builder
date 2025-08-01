from sqlalchemy import create_engine, Integer, String, Float, MetaData, ForeignKey, Index, JSON
from sqlalchemy.orm import DeclarativeBase, relationship, registry, Mapped, mapped_column, sessionmaker
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import Base

class Projects(Base): 
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    flows = relationship("Flow", back_populates="project", cascade="all, delete-orphan")