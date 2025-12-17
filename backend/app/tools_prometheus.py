"""
Prometheus tools used by the Monitoring Orchestrator agent.

These functions will later be wrapped as LangGraph / LangChain tools,
but are kept as plain Python functions here for clarity.
"""

from __future__ import annotations

from typing import Any, Dict, List

import requests

# Your Prometheus endpoint
PROMETHEUS_URL = "http://192.168.229.143:9090"


def get_prometheus_alerts() -> List[Dict[str, Any]]:
    """
    Fetch active alerts from Prometheus Alertmanager-compatible API.

    Returns a list of alert objects as provided by Prometheus.
    """
    resp = requests.get(f"{PROMETHEUS_URL}/api/v1/alerts", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", {}).get("alerts", [])


def get_metric_range(query: str, start: str, end: str, step: str) -> Dict[str, Any]:
    """
    Fetch a range query for a Prometheus metric.

    Parameters are passed directly to the /api/v1/query_range endpoint.
    """
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": step,
    }
    resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


