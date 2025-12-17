"""
FastAPI entrypoint for the AIOps monitoring backend.

For now this exposes simple health and Prometheus-debug endpoints.
Later we will add incident and agent APIs plus LangGraph integration.
"""

from __future__ import annotations

from fastapi import FastAPI

from .graph import build_graph
from .models import GraphState
from .tools_prometheus import get_prometheus_alerts

app = FastAPI(title="AIOps Monitoring Backend")

# Compile LangGraph workflow on startup.
graph = build_graph()


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


@app.post("/debug/run-graph")
def debug_run_graph() -> dict:
    """
    Run one pass of the LangGraph workflow starting from an empty state.

    This is a simple way to test that all agents and tools are wired correctly.
    """
    state = GraphState()
    result = graph.invoke(state)
    return {
        "incidents": {k: v.model_dump() for k, v in result.incidents.items()},
        "actions": [a.model_dump() for a in result.actions],
        "last_normal_report_ts": result.last_normal_report_ts,
    }


@app.get("/")
def root() -> dict:
    """
    Basic root endpoint to show that the backend is running.
    """
    return {"message": "AIOps backend is running", "prometheus_url": "http://192.168.229.143:9090"}


