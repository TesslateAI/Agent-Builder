from sqlalchemy import Integer, String, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from typing import Dict, Optional
from .base import Base

class FlowExecution(Base):
    __tablename__ = "flow_executions"
    __table_args__ = (
        Index("idx_flow_executions_flow_id", "flow_id"),
        Index("idx_flow_executions_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("flows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_data: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    flow = relationship("Flow", back_populates="executions")