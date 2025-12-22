"""
State store for persisting GraphState between graph runs.

Uses SQLite via SQLAlchemy for simplicity. In production, you might use Postgres.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .models import ActionModel, GraphState, IncidentModel

# SQLite database path
DB_PATH = "aiops_state.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class IncidentORM(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String)
    alertname: Mapped[str] = mapped_column(String)
    domain: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    labels: Mapped[Dict[str, Any]] = mapped_column(JSON)
    annotations: Mapped[Dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    auto_remediated: Mapped[bool] = mapped_column(default=False)
    assigned_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    findings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ticket_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class ActionORM(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String)
    agent: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class StateMetadataORM(Base):
    __tablename__ = "state_metadata"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)


# Create tables
Base.metadata.create_all(bind=engine)


def _incident_to_orm(incident: IncidentModel) -> IncidentORM:
    """Convert IncidentModel to ORM."""
    return IncidentORM(
        id=incident.id,
        source=incident.source,
        alertname=incident.alertname,
        domain=incident.domain,
        severity=incident.severity,
        status=incident.status,
        labels=incident.labels,
        annotations=incident.annotations,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        auto_remediated=incident.auto_remediated,
        assigned_agent=incident.assigned_agent,
        findings=incident.findings,
        recommendation=incident.recommendation,
        ticket_id=incident.ticket_id,
    )


def _orm_to_incident(orm: IncidentORM) -> IncidentModel:
    """Convert ORM to IncidentModel."""
    return IncidentModel(
        id=orm.id,
        source=orm.source,
        alertname=orm.alertname,
        domain=orm.domain,
        severity=orm.severity,
        status=orm.status,
        labels=orm.labels,
        annotations=orm.annotations,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        auto_remediated=orm.auto_remediated,
        assigned_agent=orm.assigned_agent,
        findings=orm.findings,
        recommendation=orm.recommendation,
        ticket_id=orm.ticket_id,
    )


def _action_to_orm(action: ActionModel) -> ActionORM:
    """Convert ActionModel to ORM."""
    return ActionORM(
        id=action.id,
        incident_id=action.incident_id,
        agent=action.agent,
        type=action.type,
        message=action.message,
        data=action.data,
        created_at=action.created_at,
    )


def _orm_to_action(orm: ActionORM) -> ActionModel:
    """Convert ORM to ActionModel."""
    return ActionModel(
        id=orm.id,
        incident_id=orm.incident_id,
        agent=orm.agent,
        type=orm.type,
        message=orm.message,
        data=orm.data,
        created_at=orm.created_at,
    )


def save_state(state: GraphState) -> None:
    """Persist GraphState to database."""
    db = SessionLocal()
    try:
        # Save incidents (upsert)
        for incident in state.incidents.values():
            orm = _incident_to_orm(incident)
            db.merge(orm)

        # Save actions (append only, check by ID to avoid duplicates)
        for action in state.actions:
            existing = db.get(ActionORM, action.id)
            if not existing:
                orm = _action_to_orm(action)
                db.add(orm)
            # If action exists, update it (in case message/data changed)
            elif existing:
                existing.message = action.message
                existing.data = action.data
                existing.type = action.type
                existing.agent = action.agent
                existing.incident_id = action.incident_id

        # Save metadata
        if state.last_normal_report_ts:
            ts_str = state.last_normal_report_ts.isoformat()
            metadata = db.get(StateMetadataORM, "last_normal_report_ts")
            if metadata:
                metadata.value = ts_str
            else:
                metadata = StateMetadataORM(key="last_normal_report_ts", value=ts_str)
                db.add(metadata)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def load_state() -> GraphState:
    """Load GraphState from database."""
    db = SessionLocal()
    try:
        # Load incidents
        incidents = {}
        for orm in db.query(IncidentORM).all():
            incidents[orm.id] = _orm_to_incident(orm)

        # Load actions
        actions = []
        for orm in db.query(ActionORM).order_by(ActionORM.created_at.desc()).all():
            actions.append(_orm_to_action(orm))

        # Load metadata
        last_normal_report_ts = None
        metadata = db.get(StateMetadataORM, "last_normal_report_ts")
        if metadata:
            try:
                last_normal_report_ts = datetime.fromisoformat(metadata.value)
                if last_normal_report_ts.tzinfo is None:
                    last_normal_report_ts = last_normal_report_ts.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        return GraphState(
            incidents=incidents,
            actions=actions,
            last_normal_report_ts=last_normal_report_ts,
        )
    finally:
        db.close()


def get_incidents(
    severity: Optional[str] = None,
    domain: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> List[IncidentModel]:
    """Query incidents with filters."""
    db = SessionLocal()
    try:
        query = db.query(IncidentORM)

        if severity:
            query = query.filter(IncidentORM.severity == severity)
        if domain:
            query = query.filter(IncidentORM.domain == domain)
        if status:
            query = query.filter(IncidentORM.status == status)
        if search:
            search_lower = search.lower()
            query = query.filter(
                (IncidentORM.alertname.ilike(f"%{search_lower}%"))
                | (IncidentORM.id.ilike(f"%{search_lower}%"))
            )

        results = query.order_by(IncidentORM.updated_at.desc()).all()
        return [_orm_to_incident(orm) for orm in results]
    finally:
        db.close()


def get_incident_by_id(incident_id: str) -> Optional[IncidentModel]:
    """Get a single incident by ID."""
    db = SessionLocal()
    try:
        orm = db.get(IncidentORM, incident_id)
        return _orm_to_incident(orm) if orm else None
    finally:
        db.close()


def get_actions_for_incident(incident_id: str) -> List[ActionModel]:
    """Get all actions for a specific incident."""
    db = SessionLocal()
    try:
        orms = db.query(ActionORM).filter(ActionORM.incident_id == incident_id).order_by(ActionORM.created_at.asc()).all()
        return [_orm_to_action(orm) for orm in orms]
    finally:
        db.close()


def get_recent_actions(limit: int = 50) -> List[ActionModel]:
    """Get recent actions across all incidents."""
    db = SessionLocal()
    try:
        orms = db.query(ActionORM).order_by(ActionORM.created_at.desc()).limit(limit).all()
        return [_orm_to_action(orm) for orm in orms]
    finally:
        db.close()


def get_actions_by_agent(agent: str, limit: int = 50) -> List[ActionModel]:
    """Get recent actions for a specific agent."""
    db = SessionLocal()
    try:
        orms = (
            db.query(ActionORM)
            .filter(ActionORM.agent == agent)
            .order_by(ActionORM.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_orm_to_action(orm) for orm in orms]
    finally:
        db.close()

