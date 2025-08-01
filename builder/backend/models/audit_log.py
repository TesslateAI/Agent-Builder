from sqlalchemy import Integer, String, Text, ForeignKey, Index, JSON, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, Dict
from .base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_organization_id", "organization_id"),
        Index("idx_audit_logs_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    organization_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("organizations.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    details: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )