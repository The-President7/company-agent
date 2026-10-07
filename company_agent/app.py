"""Streamlit interface for the Secretary read-only MVP."""

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import secrets
import uuid
import streamlit as st
from sqlalchemy import func, select
from company_agent.config import settings
from company_agent.db import SessionLocal, init_db
from company_agent.models import AuditEvent, Connector, MonitorEvent, MonitorIssue, MonitorProject, Report, SourceEvent
from company_agent.api import _llm_answer, _render_report_pdf
from company_agent.services import audit, draft_report, ensure_workspace, review_report, search_events

st.set_page_config(page_title="Secretary · The President", page_icon="🗂️", layout="wide")


@st.cache_resource
def _initialize() -> None:
    init_db()
    with SessionLocal() as db:
        ensure_workspace(db)


def _fmt_date(value: datetime) -> str:
    # Keep rendered timestamps stable across SQLite and Postgres values.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _source(event: SourceEvent) -> None:
    tag = " · DEMO DATA" if event.synthetic else ""
    st.markdown(f"**{event.title}**{tag}")
    st.caption(f"{event.provider.title()} · {event.event_type.replace('_', ' ')} · {event.author} · {event.source_scope} · {_fmt_date(event.occurred_at)}")
    st.write(event.content)
    if event.source_url:
        st.link_button("Open source", event.source_url)


def _dashboard() -> None:
    st.subheader("Workspace activity")
    with SessionLocal() as db:
        connectors = list(db.scalars(select(Connector).where(Connector.workspace_id == settings.workspace_id).order_by(Connector.provider)))
        events = list(db.scalars(select(SourceEvent).where(SourceEvent.workspace_id == settings.workspace_id).order_by(SourceEvent.occurred_at.desc()).limit(10)))
        reports = list(db.scalars(select(Report).where(Report.workspace_id == settings.workspace_id).order_by(Report.created_at.desc()).limit(5)))
        ready = [c for c in connectors if c.status == "connected"]
        a, b, c = st.columns(3)
        a.metric("Connected sources", f"{len(ready)} / {len(connectors)}")
        b.metric("Stored events", db.scalar(select(func.count(SourceEvent.id)).where(SourceEvent.workspace_id == settings.workspace_id)))
        c.metric("Reports awaiting review", sum(r.status == "draft" for r in reports))
        st.info("Coverage reflects records stored in this workspace. Live sync requires configured provider credentials.")
        st.markdown("#### Source health")
        for connector in connectors:
            label = connector.provider.replace("_", " ").title()
            detail = connector.last_error or (f"Last synced {_fmt_date(connector.last_synced_at)}" if connector.last_synced_at else "No sync recorded")
            st.write(f"**{label}:** {connector.status.replace('_', ' ').title()} · {detail}")
        st.markdown("#### Recent activity")
        if events:
            for event in events:
                with st.container(border=True):
                    _source(event)
        else:
            st.caption("No source events yet. Add provider adapters or enable sample fixtures.")
        if reports:
            st.markdown("#### Recent reports")
            for report in reports:
                st.write(f"**{report.title}** · {report.status.title()} · {report.period_start.date()} to {report.period_end.date()}")


def _ask() -> None:
    st.subheader("Ask about company activity")
    st.caption("Answers use the configured LLM and cite matching workspace records.")
    with st.form("ask_form"):
        question = st.text_input("Question", placeholder="What decisions and follow-ups came up recently?")
        days = st.selectbox("Look back", [7, 30, 90, 365], index=1)
        submitted = st.form_submit_button("Search evidence", type="primary")
    if submitted and question.strip():
        end = datetime.now(timezone.utc) + timedelta(seconds=1)
        start = end - timedelta(days=days)
        with SessionLocal() as db:
            results = search_events(db, question, start, end)
            try:
                answer = _llm_answer(question, results)
                audit(db, "assistant.llm_answered", "source_events", details=f"{len(results)} evidence records")
            except Exception as exc:
                answer = None
                detail = getattr(exc, "detail", "") or str(exc) or "Unexpected provider error"
                st.error(f"Could not generate an LLM answer: {detail}")
            db.commit()
        if answer:
            st.markdown("#### Answer")
            st.write(answer)
        if results:
            st.markdown(f"#### Evidence found ({len(results)})")
            if any(e.synthetic for e in results):
                st.warning("Some results are synthetic demo records. Confirm claims against the linked source before relying on them.")
            for event in results:
                with st.container(border=True):
                    _source(event)
        else:
            st.warning("No matching records were found in the selected window. This may reflect missing connector access or sync gaps, not absence of activity.")
    elif submitted:
        st.warning("Enter a question to search.")


def _reports() -> None:
    st.subheader("Monthly reports")
    st.caption("Drafts include links to their supporting records and a coverage statement. Download reports as PDFs.")
    default_end = date.today().replace(day=1)
    default_start = (default_end - timedelta(days=1)).replace(day=1)
    with st.form("report_form"):
        c1, c2 = st.columns(2)
        start_day = c1.date_input("Period starts", value=default_start)
        end_day = c2.date_input("Period ends (exclusive)", value=default_end)
        make_draft = st.form_submit_button("Generate report draft", type="primary")
    if make_draft:
        if start_day >= end_day:
            st.error("The end date must be after the start date.")
        else:
            start = datetime.combine(start_day, time.min, tzinfo=timezone.utc)
            end = datetime.combine(end_day, time.min, tzinfo=timezone.utc)
            with SessionLocal() as db:
                report = draft_report(db, start, end)
                st.success(f"Draft report #{report.id} created.")
            st.rerun()
    with SessionLocal() as db:
        reports = list(db.scalars(select(Report).where(Report.workspace_id == settings.workspace_id).order_by(Report.created_at.desc()).limit(30)))
        for report in reports:
            with st.expander(f"#{report.id} · {report.title} · {report.status.title()} · {report.period_start.date()} to {report.period_end.date()}", expanded=report.status == "draft"):
                st.caption(report.coverage_note)
                st.markdown(report.body)
                st.download_button("Download PDF", _render_report_pdf(db, report),
                    file_name=f"secretary-report-{report.id}.pdf", mime="application/pdf",
                    key=f"report-pdf-{report.id}")
                if report.status == "draft":
                    left, right = st.columns(2)
                    if left.button("Approve draft", key=f"approve-{report.id}", type="primary"):
                        review_report(db, report, True)
                        st.rerun()
                    if right.button("Reject draft", key=f"reject-{report.id}"):
                        review_report(db, report, False)
                        st.rerun()
                elif report.reviewed_at:
                    st.caption(f"Reviewed by {report.reviewed_by} at {_fmt_date(report.reviewed_at)}")


def _connectors() -> None:
    st.subheader("Connectors")
    st.caption("Set provider credentials in the service environment. Then use the authenticated API docs to run Slack/GitHub sync or configure the WhatsApp Business webhook.")
    st.code("uv run secretary-api\n# Open http://localhost:8000/docs\n"
            "# POST /connectors/slack/sync with X-Channel-Ids\n"
            "# POST /connectors/github/sync uses GITHUB_REPOSITORIES", language="bash")
    with SessionLocal() as db:
        connectors = list(db.scalars(select(Connector).where(Connector.workspace_id == settings.workspace_id).order_by(Connector.provider)))
        for connector in connectors:
            with st.container(border=True):
                st.markdown(f"### {connector.provider.replace('_', ' ').title()}")
                st.write(f"Status: **{connector.status.replace('_', ' ').title()}**")
                st.write(f"Granted scope: {connector.scopes or 'None recorded'}")
                if connector.last_synced_at:
                    st.write(f"Last successful sync: {_fmt_date(connector.last_synced_at)}")
                if connector.last_error:
                    st.error(connector.last_error)
                if connector.status != "not_connected":
                    if st.button(f"Mark {connector.provider} disconnected", key=f"disconnect-{connector.id}"):
                        connector.status = "not_connected"
                        connector.scopes = ""
                        connector.last_error = None
                        audit(db, "connector.disconnected", "connector", str(connector.id), connector.provider)
                        db.commit()
                        st.rerun()
        st.caption("WhatsApp uses the signed Business webhook at /webhooks/whatsapp and only accepts configured phone-number IDs. Personal accounts are out of scope.")


def _audit() -> None:
    st.subheader("Audit history")
    with SessionLocal() as db:
        rows = list(db.scalars(select(AuditEvent).where(AuditEvent.workspace_id == settings.workspace_id).order_by(AuditEvent.created_at.desc()).limit(200)))
        if not rows:
            st.caption("No actions recorded yet.")
        for row in rows:
            st.write(f"{_fmt_date(row.created_at)} · **{row.action}** · {row.actor_id} · {row.target_type} {row.target_id} · {row.details}")


def _monitoring() -> None:
    st.subheader("Application monitoring")
    st.caption("Create a project key, install a client SDK, then inspect grouped errors and performance events.")
    with st.form("monitor_project"):
        name = st.text_input("Application name", placeholder="Customer portal")
        create = st.form_submit_button("Create monitoring project", type="primary")
    if create and name.strip():
        project_key = "sec_" + secrets.token_urlsafe(32)
        with SessionLocal() as db:
            project = MonitorProject(id=str(uuid.uuid4()), workspace_id=settings.workspace_id,
                name=name.strip(), api_key_hash=hashlib.sha256(project_key.encode()).hexdigest())
            db.add(project)
            audit(db, "monitor.project_created", "monitor_project", project.id, project.name)
            db.commit()
        st.session_state["new_monitor_project_key"] = project_key
    if st.session_state.get("new_monitor_project_key"):
        st.warning("Copy this project key now. It will not be shown again.")
        st.code(st.session_state["new_monitor_project_key"])
        st.code("const monitor = new SecretaryMonitor({ projectKey, endpoint: 'https://YOUR_HOST' });\n"
                "monitor.installGlobalHandlers();", language="javascript")
    with SessionLocal() as db:
        projects = list(db.scalars(select(MonitorProject).where(
            MonitorProject.workspace_id == settings.workspace_id).order_by(MonitorProject.created_at.desc())))
        if not projects:
            st.info("No monitored applications yet.")
        for project in projects:
            with st.expander(project.name):
                since = datetime.now(timezone.utc) - timedelta(hours=24)
                recent = list(db.scalars(select(MonitorEvent).where(
                    MonitorEvent.project_id == project.id, MonitorEvent.occurred_at >= since)))
                durations = sorted(event.duration_ms for event in recent
                    if event.event_type == "transaction" and event.duration_ms is not None)
                p95 = durations[min(int(len(durations) * 0.95), len(durations) - 1)] if durations else None
                a, b, c = st.columns(3)
                a.metric("Errors · 24h", sum(event.event_type == "error" for event in recent))
                b.metric("Transactions · 24h", len(durations))
                c.metric("p95 duration", f"{p95:.0f} ms" if p95 is not None else "—")
                issues = list(db.scalars(select(MonitorIssue).where(MonitorIssue.project_id == project.id)
                    .order_by(MonitorIssue.last_seen_at.desc()).limit(100)))
                if not issues:
                    st.caption("No errors or transactions received yet.")
                for issue in issues:
                    st.markdown(f"**{issue.title}** · {issue.event_type} · {issue.occurrence_count} occurrences")
                    st.caption(f"{issue.environment} · last seen {_fmt_date(issue.last_seen_at)} · {issue.release}")
                    if issue.stacktrace:
                        st.code(issue.stacktrace[:8000])


def main() -> None:
    _initialize()
    st.title("Secretary")
    st.caption(f"Company operations assistant · {settings.workspace_name}")
    page = st.sidebar.radio("Workspace", ["Overview", "Ask", "Reports", "Connectors", "Monitoring", "Audit"])
    if page == "Overview":
        _dashboard()
    elif page == "Ask":
        _ask()
    elif page == "Reports":
        _reports()
    elif page == "Connectors":
        _connectors()
    elif page == "Monitoring":
        _monitoring()
    else:
        _audit()


if __name__ == "__main__":
    main()
