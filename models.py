"""Minimal normalized records for the read-only MVP and its review workflow."""

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Connector(Base):
    __tablename__ = "connectors"
    __table_args__ = (UniqueConstraint("workspace_id", "provider", name="uq_connector_workspace_provider"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="not_connected", nullable=False)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class SourceEvent(Base):
    __tablename__ = "source_events"
    __table_args__ = (
        UniqueConstraint("workspace_id", "provider", "provider_event_id", name="uq_event_provider_id"),
        Index("ix_event_workspace_time", "workspace_id", "occurred_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(240), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    author: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_scope: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[str] = mapped_column(Text, default="", nullable=False)
    coverage_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(60), nullable=False)
    target_id: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MonitorProject(Base):
    __tablename__ = "monitor_projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MonitorIssue(Base):
    __tablename__ = "monitor_issues"
    __table_args__ = (UniqueConstraint("project_id", "fingerprint", name="uq_monitor_project_fingerprint"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("monitor_projects.id", ondelete="CASCADE"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    environment: Mapped[str] = mapped_column(String(100), default="production", nullable=False)
    release: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    stacktrace: Mapped[str] = mapped_column(Text, default="", nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MonitorEvent(Base):
    __tablename__ = "monitor_events"
    __table_args__ = (Index("ix_monitor_event_project_time", "project_id", "occurred_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("monitor_projects.id", ondelete="CASCADE"), index=True)
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("monitor_issues.id", ondelete="SET NULL"), index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(100), default="production", nullable=False)
    release: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    stacktrace: Mapped[str] = mapped_column(Text, default="", nullable=False)
    duration_ms: Mapped[float | None] = mapped_column()
    url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
