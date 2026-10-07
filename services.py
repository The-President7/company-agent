"""Workspace-scoped retrieval, fixture data, reports, and auditable review actions."""

import json
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from config import settings
from models import AuditEvent, Connector, Report, SourceEvent, Workspace


def audit(db: Session, action: str, target_type: str, target_id: str = "", details: str = "") -> None:
    db.add(AuditEvent(workspace_id=settings.workspace_id, actor_id=settings.user_id,
                      action=action, target_type=target_type, target_id=target_id, details=details[:1000]))


def ensure_workspace(db: Session) -> None:
    workspace = db.get(Workspace, settings.workspace_id)
    if workspace is None:
        db.add(Workspace(id=settings.workspace_id, name=settings.workspace_name))
        db.flush()
    for provider in ("slack", "github", "calendar", "whatsapp_business"):
        exists = db.scalar(select(Connector.id).where(
            Connector.workspace_id == settings.workspace_id, Connector.provider == provider))
        if not exists:
            db.add(Connector(workspace_id=settings.workspace_id, provider=provider,
                             status="not_connected", scopes=""))
    db.flush()
    if settings.seed_demo_data:
        seed_demo_events(db)
    db.commit()


def seed_demo_events(db: Session) -> None:
    """Create labeled synthetic records once, so the app is useful before OAuth setup."""
    if db.scalar(select(SourceEvent.id).where(
            SourceEvent.workspace_id == settings.workspace_id, SourceEvent.synthetic.is_(True))):
        return
    now = datetime.now(timezone.utc)
    items = [
        ("github", "pull_request", "Reduce API latency in dashboard", "Caching reduced median dashboard API latency in staging; rollout is pending review.", "A. Kim", "engineering", "https://example.org/demo/pull/184", 2),
        ("slack", "decision", "Q4 onboarding focus", "Team agreed to prioritize guided setup and defer billing experiments until onboarding metrics stabilize.", "M. Patel", "#product", "https://example.org/demo/slack/decision-42", 4),
        ("github", "issue", "Investigate intermittent webhook retries", "Retries are elevated for a subset of tenants. Need compare provider response codes and deduplication behavior.", "J. Rivera", "platform", "https://example.org/demo/issues/93", 6),
        ("slack", "meeting", "Customer advisory follow-up", "Follow-up: share revised migration guide with the advisory group before the next session.", "S. Chen", "#customer-success", "https://example.org/demo/slack/meeting-17", 8),
        ("github", "release", "Secretary ingestion v0.3", "Release adds event deduplication and connector health reporting for the staging workspace.", "A. Kim", "releases", "https://example.org/demo/releases/0.3", 10),
    ]
    for provider, kind, title, content, author, scope, url, days_ago in items:
        db.add(SourceEvent(workspace_id=settings.workspace_id, provider=provider,
                           provider_event_id=f"demo-{provider}-{kind}-{days_ago}", event_type=kind,
                           title=title, content=content, author=author, source_url=url,
                           source_scope=scope, occurred_at=now-timedelta(days=days_ago), synthetic=True))


def search_events(db: Session, query: str, start: datetime | None = None,
                  end: datetime | None = None, limit: int = 20) -> list[SourceEvent]:
    """Retrieve within the active workspace first; ranking never crosses workspace boundaries."""
    stmt = select(SourceEvent).where(SourceEvent.workspace_id == settings.workspace_id)
    if start:
        stmt = stmt.where(SourceEvent.occurred_at >= start)
    if end:
        stmt = stmt.where(SourceEvent.occurred_at < end)
    rows = list(db.scalars(stmt.order_by(SourceEvent.occurred_at.desc()).limit(500)))
    tokens = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2}
    if not tokens:
        return rows[:limit]
    ranked = []
    for row in rows:
        haystack = f"{row.title} {row.content} {row.event_type} {row.source_scope}".lower()
        score = sum(haystack.count(token) for token in tokens)
        if score:
            ranked.append((score, row.occurred_at, row))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [row for _, _, row in ranked[:limit]]


def draft_report(db: Session, start: datetime, end: datetime) -> Report:
    events = search_events(db, "", start, end, limit=500)
    buckets: dict[str, list[SourceEvent]] = {}
    for event in events:
        buckets.setdefault(event.event_type, []).append(event)
    labels = {"release": "Shipped work", "decision": "Key decisions", "meeting": "Meetings and follow-ups",
              "issue": "Risks and blockers", "security_alert": "Security alerts", "pull_request": "Engineering activity"}
    sections = []
    for kind, heading in labels.items():
        if kind not in buckets:
            continue
        sections.append(f"## {heading}")
        for event in buckets[kind]:
            sections.append(f"- **{event.title}** — {event.content} ([source]({event.source_url}))")
    if not sections:
        sections = ["No eligible source events were found for this period."]
    connectors = list(db.scalars(select(Connector).where(Connector.workspace_id == settings.workspace_id)))
    active = [c.provider for c in connectors if c.status == "connected"]
    missing = [c.provider for c in connectors if c.status != "connected"]
    synthetic = sum(1 for e in events if e.synthetic)
    coverage = (f"Connected sources: {', '.join(active) if active else 'none'}. "
                f"Unavailable or unconfigured: {', '.join(missing) if missing else 'none'}. "
                f"Evidence records: {len(events)}; synthetic demo records: {synthetic}. "
                "This report covers stored records only; it does not imply complete company activity.")
    body = "\n\n".join(sections)
    report = Report(workspace_id=settings.workspace_id, title="Monthly operations report",
                    period_start=start, period_end=end, status="draft", body=body,
                    evidence_ids=json.dumps([e.id for e in events]), coverage_note=coverage,
                    created_by=settings.user_id)
    db.add(report)
    db.flush()
    audit(db, "report.drafted", "report", str(report.id), f"{start.date()} through {end.date()}; {len(events)} evidence records")
    db.commit()
    return report


def review_report(db: Session, report: Report, approve: bool) -> None:
    # Only drafts can transition; editing a report after approval must return it to draft.
    if report.status != "draft":
        raise ValueError("Only draft reports can be reviewed.")
    report.status = "approved" if approve else "rejected"
    report.reviewed_by = settings.user_id
    report.reviewed_at = datetime.now(timezone.utc)
    audit(db, "report.approved" if approve else "report.rejected", "report", str(report.id))
    db.commit()
