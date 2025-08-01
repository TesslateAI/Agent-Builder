from sqlalchemy import create_engine, Integer, String, Float, MetaData, ForeignKey, Index, JSON
from sqlalchemy.orm import DeclarativeBase, relationship, registry, Mapped, mapped_column, sessionmaker
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import Base

class Flow(Base):
    __tablename__ = "flows"
    __table_args__ = (
        Index("idx_flows_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    nodes: Mapped[List[Dict]] = mapped_column(JSON, nullable=False)
    edges: Mapped[List[Dict]] = mapped_column(JSON, nullable=False)
    metadata: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    project = relationship("Project", back_populates="flows")
    executions = relationship("FlowExecution", back_populates="flow", cascade="all, delete-orphan")
