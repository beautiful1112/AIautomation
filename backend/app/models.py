"""
Core data models for incidents, actions, and shared graph state.

These models mirror the design described in README.md and will be used both
by the LangGraph state and by the FastAPI layer for serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IncidentModel(BaseModel):
    id: str
    source: str
    alertname: str
    domain: str  # "k8s" or "network"
    severity: str  # "low" | "medium" | "high" | "unknown"
    status: str  # "new" | "investigating" | "auto_remediated" | "awaiting_human" | "resolved"
    labels: Dict[str, str]
    annotations: Dict[str, str]
    created_at: datetime
    updated_at: datetime
    auto_remediated: bool = False
    assigned_agent: Optional[str] = None
    findings: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None
    ticket_id: Optional[str] = None


class ActionModel(BaseModel):
    id: str
    incident_id: str
    agent: str  # "monitor" | "k8s" | "network" | "review" | "ticket"
    type: str
    message: str
    data: Optional[Dict[str, Any]] = None
    created_at: datetime


class GraphState(BaseModel):
    incidents: Dict[str, IncidentModel] = Field(default_factory=dict)
    actions: List[ActionModel] = Field(default_factory=list)
    last_normal_report_ts: Optional[datetime] = None


