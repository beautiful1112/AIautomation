"""
FastAPI entrypoint for the AIOps monitoring backend.

Exposes REST API endpoints for the frontend and debug endpoints.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .graph import build_graph
from .models import ActionModel, GraphState, IncidentModel
from .store import (
    get_actions_by_agent,
    get_actions_for_incident,
    get_incident_by_id,
    get_incidents,
    get_recent_actions,
    load_state,
    save_state,
)
from .tools_prometheus import get_prometheus_alerts

app = FastAPI(title="AIOps Monitoring Backend")

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://192.168.229.130:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compile LangGraph workflow on startup.
graph = build_graph()

# Background task control
_monitoring_active = True
_monitoring_thread: Optional[threading.Thread] = None
_last_run_time: Optional[datetime] = None
_last_run_status: dict = {"status": "idle", "error": None}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/debug/prometheus-alerts")
def debug_prometheus_alerts() -> dict:
    """
    Simple endpoint to verify connectivity to Prometheus at 192.168.229.143:9090.
    """
    alerts = get_prometheus_alerts()
    return {"count": len(alerts), "alerts": alerts}


def _run_graph_once() -> dict:
    """
    Internal function to run one graph execution cycle.
    Returns status dict with success/error info.
    """
    try:
        # Load current state
        state = load_state()
        # Run graph (LangGraph returns dict, convert to GraphState)
        result_dict = graph.invoke(state)
        result = GraphState(**result_dict)
        # Save updated state
        save_state(result)
        return {
            "status": "success",
            "incidents_count": len(result.incidents),
            "actions_count": len(result.actions),
            "last_normal_report_ts": result.last_normal_report_ts.isoformat() if result.last_normal_report_ts else None,
            "error": None,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "incidents_count": 0,
            "actions_count": 0,
        }


@app.post("/api/run-graph")
def run_graph_manual() -> dict:
    """
    Manually trigger one execution of the LangGraph workflow.
    
    This endpoint can be called from the frontend to manually trigger agent execution.
    """
    global _last_run_time, _last_run_status
    
    _last_run_time = datetime.now(timezone.utc)
    _last_run_status = _run_graph_once()
    _last_run_status["run_time"] = _last_run_time.isoformat()
    
    return {
        "message": "Graph execution triggered",
        **(_last_run_status),
    }


@app.post("/debug/run-graph")
def debug_run_graph() -> dict:
    """
    Run one pass of the LangGraph workflow using persistent state.

    This loads the current state, runs the graph, saves the result, and returns it.
    """
    result = _run_graph_once()
    if result["status"] == "success":
        state = load_state()
        return {
            "incidents": {k: v.model_dump() for k, v in state.incidents.items()},
            "actions": [a.model_dump() for a in state.actions],
            "last_normal_report_ts": result.get("last_normal_report_ts"),
        }
    else:
        return {"error": result.get("error")}


def _monitoring_loop():
    """
    Background thread that continuously polls Prometheus and runs the graph.
    Runs every 30 seconds by default.
    """
    global _monitoring_active, _last_run_time, _last_run_status
    
    while _monitoring_active:
        try:
            _last_run_time = datetime.now(timezone.utc)
            _last_run_status = _run_graph_once()
            _last_run_status["run_time"] = _last_run_time.isoformat()
        except Exception as e:
            _last_run_status = {
                "status": "error",
                "error": str(e),
                "run_time": _last_run_time.isoformat() if _last_run_time else None,
            }
        
        # Sleep for 30 seconds before next run
        for _ in range(30):
            if not _monitoring_active:
                break
            threading.Event().wait(1)


@app.on_event("startup")
def start_monitoring():
    """
    Start the background monitoring thread when FastAPI starts.
    """
    global _monitoring_thread, _monitoring_active
    
    _monitoring_active = True
    _monitoring_thread = threading.Thread(target=_monitoring_loop, daemon=True)
    _monitoring_thread.start()


@app.on_event("shutdown")
def stop_monitoring():
    """
    Stop the background monitoring thread when FastAPI shuts down.
    """
    global _monitoring_active
    
    _monitoring_active = False


@app.get("/api/monitoring-status")
def get_monitoring_status() -> dict:
    """
    Get the status of the automatic monitoring loop.
    """
    return {
        "active": _monitoring_active,
        "last_run_time": _last_run_time.isoformat() if _last_run_time else None,
        "last_run_status": _last_run_status,
    }


@app.get("/")
def root() -> dict:
    """
    Basic root endpoint to show that the backend is running.
    """
    return {"message": "AIOps backend is running", "prometheus_url": "http://192.168.229.143:9090"}


# ============================================================================
# REST API Endpoints for Frontend
# ============================================================================


@app.get("/api/status")
def get_status() -> dict:
    """
    Returns summary for dashboard:
    - overall_status (healthy/degraded)
    - last_normal_report
    - stats (active_incidents, k8s_incidents, network_incidents, auto_remediations_24h)
    """
    state = load_state()

    # Calculate stats
    active_incidents = [inc for inc in state.incidents.values() if inc.status not in {"resolved", "auto_remediated"}]
    k8s_incidents = [inc for inc in active_incidents if inc.domain == "k8s"]
    network_incidents = [inc for inc in active_incidents if inc.domain == "network"]

    # Count auto-remediations in last 24h
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours=24)
    auto_remediations_24h = sum(
        1
        for action in state.actions
        if action.type == "remediation" and action.created_at >= yesterday
    )

    # Determine overall status
    high_severity_active = any(inc.severity == "high" for inc in active_incidents)
    overall_status = "degraded" if active_incidents or high_severity_active else "healthy"

    # Last normal report
    last_normal_report = None
    if state.last_normal_report_ts:
        # Find the most recent normal_report action
        normal_actions = [
            a for a in state.actions
            if a.type == "normal_report" and a.created_at <= state.last_normal_report_ts
        ]
        if normal_actions:
            latest = max(normal_actions, key=lambda a: a.created_at)
            last_normal_report = {
                "text": latest.message,
                "timestamp": latest.created_at.isoformat(),
            }
        else:
            last_normal_report = {
                "text": "System healthy. No active alerts.",
                "timestamp": state.last_normal_report_ts.isoformat(),
            }

    return {
        "overall_status": overall_status,
        "last_normal_report": last_normal_report,
        "stats": {
            "active_incidents": len(active_incidents),
            "k8s_incidents": len(k8s_incidents),
            "network_incidents": len(network_incidents),
            "auto_remediations_24h": auto_remediations_24h,
        },
    }


@app.get("/api/incidents")
def list_incidents(
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, unknown"),
    domain: Optional[str] = Query(None, description="Filter by domain: k8s, network"),
    status: Optional[str] = Query(None, description="Filter by status: new, investigating, auto_remediated, awaiting_human, resolved"),
    search: Optional[str] = Query(None, description="Search in alertname and incident ID"),
) -> dict:
    """
    Returns a list of incidents with basic info.
    Supports filtering by severity, domain, status, and text search.
    """
    incidents = get_incidents(severity=severity, domain=domain, status=status, search=search)
    return {
        "incidents": [inc.model_dump() for inc in incidents],
        "count": len(incidents),
    }


@app.get("/api/incidents/{incident_id}")
def get_incident_detail(incident_id: str) -> dict:
    """
    Returns full incident data including timeline of actions.
    """
    incident = get_incident_by_id(incident_id)
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Incident not found")

    actions = get_actions_for_incident(incident_id)
    return {
        "incident": incident.model_dump(),
        "actions": [action.model_dump() for action in actions],
    }


@app.get("/api/agents")
def list_agents() -> list[dict]:
    """
    Returns agent stats:
    - agent name
    - lastActiveAt
    - incidentsHandled
    - actionsPerformed
    - autoRemediations
    """
    state = load_state()

    agents = ["monitor", "k8s", "network", "review", "ticket"]
    stats = []

    for agent_name in agents:
        agent_actions = [a for a in state.actions if a.agent == agent_name]
        if not agent_actions:
            stats.append({
                "agent": agent_name,
                "lastActiveAt": None,
                "incidentsHandled": 0,
                "actionsPerformed": 0,
                "autoRemediations": 0,
            })
            continue

        last_active = max(agent_actions, key=lambda a: a.created_at).created_at
        incidents_handled = len(set(a.incident_id for a in agent_actions if a.incident_id != "none"))
        auto_remediations = sum(1 for a in agent_actions if a.type == "remediation")

        stats.append({
            "agent": agent_name,
            "lastActiveAt": last_active.isoformat(),
            "incidentsHandled": incidents_handled,
            "actionsPerformed": len(agent_actions),
            "autoRemediations": auto_remediations,
        })

    return stats


@app.get("/api/agents/{agent}/activity")
def get_agent_activity(agent: str, limit: int = Query(50, ge=1, le=200)) -> dict:
    """
    Returns recent actions taken by one agent.
    """
    actions = get_actions_by_agent(agent, limit=limit)
    return {
        "agent": agent,
        "actions": [action.model_dump() for action in actions],
        "count": len(actions),
    }


@app.get("/api/activity/recent")
def get_recent_activity(limit: int = Query(50, ge=1, le=200)) -> dict:
    """
    Returns recent actions across all agents (for dashboard activity feed).
    """
    actions = get_recent_actions(limit=limit)
    return {
        "actions": [action.model_dump() for action in actions],
        "count": len(actions),
    }


