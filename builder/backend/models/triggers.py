from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from .base import Base
import uuid

class Triggers(Base):
    __tablename__ = 'triggers'
    
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    flow_id: Mapped[str] = mapped_column(String(64), ForeignKey('flows.id', ondelete='CASCADE'), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'webhook', 'schedule', 'event', 'email', 'file'
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)  # JSONB config for trigger
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey('users.id'), nullable=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey('organizations.id'), nullable=True)
    
    # Trigger-specific metadata
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # for webhook triggers
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # for scheduled triggers
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trigger_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships - simplified for initial testing
    # flow = relationship("Flow", back_populates="triggers")
    # creator = relationship("Users", foreign_keys=[created_by])
    # organization = relationship("Organizations", foreign_keys=[organization_id])
    executions = relationship("TriggerExecutions", back_populates="trigger", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_triggers_flow_id', 'flow_id'),
        Index('idx_triggers_type', 'type'),
        Index('idx_triggers_enabled', 'enabled'),
        Index('idx_triggers_next_run', 'next_run_at'),
        # Note: Unique constraint on webhook_url removed for SQLite compatibility
    )


class TriggerExecutions(Base):
    __tablename__ = 'trigger_executions'
    
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    trigger_id: Mapped[str] = mapped_column(String(64), ForeignKey('triggers.id', ondelete='CASCADE'), nullable=False)
    flow_execution_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey('flow_executions.id'), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # 'success', 'failure', 'timeout', 'running'
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # JSONB payload
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships - simplified for initial testing
    trigger = relationship("Triggers", back_populates="executions")
    # flow_execution = relationship("FlowExecution", foreign_keys=[flow_execution_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_executions_trigger_id', 'trigger_id'),
        Index('idx_executions_triggered_at', 'triggered_at'),
        Index('idx_executions_status', 'status'),
    )