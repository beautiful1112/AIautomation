"""
LangGraph agents (nodes) implementing the monitoring, k8s, network,
review and ticket logic at a high level.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from .llm import get_llm
from .models import ActionModel, GraphState, IncidentModel
from .tools_k8s import get_pod_events, get_pod_status, restart_pod
from .tools_network import check_device_status, check_interface_status
from .tools_prometheus import get_prometheus_alerts
from .tools_ticket import create_ticket, notify_slack


def _log_action(state: GraphState, agent: str, type_: str, message: str, data: Dict[str, Any] | None = None) -> None:
    """
    Append an ActionModel to the graph state.
    """
    action = ActionModel(
        id=f"act-{len(state.actions) + 1}",
        incident_id=data.get("incident_id") if data else "none",
        agent=agent,
        type=type_,
        message=message,
        data=data,
        created_at=datetime.utcnow(),
    )
    state.actions.append(action)


def monitor_node(state: GraphState) -> GraphState:
    """
    Monitoring Orchestrator:
    - Polls Prometheus alerts.
    - Creates or updates incidents in the shared state.
    """
    alerts = get_prometheus_alerts()
    now = datetime.utcnow()

    if not alerts:
        if not state.last_normal_report_ts or (now - state.last_normal_report_ts).total_seconds() >= 300:
            _log_action(
                state,
                agent="monitor",
                type_="normal_report",
                message="System healthy. No active alerts.",
                data={},
            )
            state.last_normal_report_ts = now
        return state

    for alert in alerts:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        alertname = labels.get("alertname", "unknown")
        incident_id = labels.get("incident_id", alertname)

        domain = "k8s" if "namespace" in labels or "pod" in labels else "network"

        existing = state.incidents.get(incident_id)
        if existing is None:
            incident = IncidentModel(
                id=incident_id,
                source="prometheus",
                alertname=alertname,
                domain=domain,
                severity="unknown",
                status="new",
                labels=labels,
                annotations=annotations,
                created_at=now,
                updated_at=now,
            )
            state.incidents[incident_id] = incident
        else:
            existing.updated_at = now
            existing.status = "new"

        _log_action(
            state,
            agent="monitor",
            type_="alert_received",
            message=f"Alert {alertname} classified as {domain}",
            data={"incident_id": incident_id, "labels": labels},
        )

    return state


def k8s_node(state: GraphState) -> GraphState:
    """
    Kubernetes Agent: inspects K8s-related incidents.
    """
    llm = get_llm()

    for incident in state.incidents.values():
        if incident.domain != "k8s" or incident.status != "new":
            continue

        namespace = incident.labels.get("namespace", "default")
        pod_name = incident.labels.get("pod") or incident.labels.get("pod_name")
        if not pod_name:
            continue

        status = get_pod_status(namespace, pod_name)
        events = get_pod_events(namespace, pod_name)

        prompt = (
            "You are a Kubernetes SRE. Analyze the following pod status and events. "
            "Summarize the likely root cause in one short paragraph.\n\n"
            f"Status: {status}\n\nEvents:\n" + "\n".join(events)
        )
        summary = llm.invoke(prompt)

        incident.findings = {
            "pod_status": status,
            "events": events,
        }
        incident.recommendation = str(summary)
        incident.assigned_agent = "k8s"
        incident.status = "investigating"
        incident.updated_at = datetime.utcnow()

        _log_action(
            state,
            agent="k8s",
            type_="investigation",
            message=f"Investigated pod {namespace}/{pod_name}",
            data={"incident_id": incident.id},
        )

    return state


def network_node(state: GraphState) -> GraphState:
    """
    Network Agent: inspects network-related incidents.
    """
    llm = get_llm()

    for incident in state.incidents.values():
        if incident.domain != "network" or incident.status != "new":
            continue

        device_id = incident.labels.get("device") or incident.labels.get("instance")
        interface_id = incident.labels.get("interface")

        if not device_id:
            continue

        device_status = check_device_status(device_id)
        interface_status = None
        if interface_id:
            interface_status = check_interface_status(device_id, interface_id)

        prompt = (
            "You are a Network SRE. Analyze the following device and interface data. "
            "Summarize the likely root cause in one short paragraph.\n\n"
            f"Device status: {device_status}\n\nInterface status: {interface_status}\n"
        )
        summary = llm.invoke(prompt)

        incident.findings = {
            "device_status": device_status,
            "interface_status": interface_status,
        }
        incident.recommendation = str(summary)
        incident.assigned_agent = "network"
        incident.status = "investigating"
        incident.updated_at = datetime.utcnow()

        _log_action(
            state,
            agent="network",
            type_="investigation",
            message=f"Investigated device {device_id}",
            data={"incident_id": incident.id},
        )

    return state


def review_node(state: GraphState) -> GraphState:
    """
    Review Agent:
    - Looks at incidents with findings.
    - Decides severity and whether to auto-remediate or escalate.
    """
    llm = get_llm()

    for incident in state.incidents.values():
        if incident.status not in {"investigating", "new"}:
            continue

        findings = incident.findings or {}
        prompt = (
            "You are a senior SRE. Given this incident and findings, "
            "assign a severity (low, medium, high) and say whether it is safe to auto-remediate. "
            "Respond in JSON with keys: severity and auto_remediate (true/false).\n\n"
            f"Incident: {incident.model_dump()}\n\nFindings: {findings}"
        )
        raw = llm.invoke(prompt)

        severity = "unknown"
        auto_remediate = False
        try:
            import json

            parsed = json.loads(str(raw))
            severity = parsed.get("severity", "unknown")
            auto_remediate = bool(parsed.get("auto_remediate", False))
        except Exception:
            severity = "unknown"
            auto_remediate = False

        incident.severity = severity

        if auto_remediate and incident.domain == "k8s":
            namespace = incident.labels.get("namespace", "default")
            pod_name = incident.labels.get("pod") or incident.labels.get("pod_name")
            if pod_name:
                restart_pod(namespace, pod_name)
                incident.auto_remediated = True
                incident.status = "auto_remediated"
                _log_action(
                    state,
                    agent="review",
                    type_="remediation",
                    message=f"Auto-restarted pod {namespace}/{pod_name}",
                    data={"incident_id": incident.id},
                )
                continue

        if severity == "high" or not auto_remediate:
            ticket_info = create_ticket(incident.model_dump())
            notify_slack(
                channel="#aiops-lab",
                message=f"High severity incident {incident.id} requires attention. Ticket {ticket_info['ticket_id']}.",
            )
            incident.ticket_id = ticket_info["ticket_id"]
            incident.status = "awaiting_human"
            _log_action(
                state,
                agent="review",
                type_="escalation",
                message=f"Escalated incident {incident.id} with ticket {incident.ticket_id}",
                data={"incident_id": incident.id},
            )

        incident.updated_at = datetime.utcnow()

    return state


def ticket_node(state: GraphState) -> GraphState:
    """
    Ticket Agent node.

    In this minimal implementation, the Review Agent already calls ticket tools
    directly, so this node is a no-op placeholder.
    """
    return state


