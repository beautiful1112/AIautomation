"""
LangGraph agents (nodes) implementing the monitoring, k8s, network,
review and ticket logic at a high level.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .llm import llm as ollama_llm
from .models import ActionModel, GraphState, IncidentModel
from .tools_k8s import get_pod_events, get_pod_status, restart_pod
from .tools_network import check_device_status, check_interface_status
from .tools_prometheus import get_prometheus_alerts
from .tools_ticket import create_ticket, notify_slack


def _log_action(state: GraphState, agent: str, type_: str, message: str, data: Dict[str, Any] | None = None) -> None:
    """
    Append an ActionModel to the graph state.
    Use timestamp-based ID to ensure uniqueness across runs.
    """
    import time
    
    # Generate unique ID using timestamp and random component
    timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000000)
    action_id = f"act-{timestamp_ms}-{len(state.actions)}"
    
    action = ActionModel(
        id=action_id,
        incident_id=(data or {}).get("incident_id", "none"),
        agent=agent,
        type=type_,
        message=message,
        data=data,
        created_at=datetime.now(timezone.utc),
    )
    state.actions.append(action)


def monitor_node(state: GraphState) -> GraphState:
    """
    Monitoring Orchestrator:
    - Polls Prometheus alerts.
    - Creates or updates incidents in the shared state.
    """
    _log_action(
        state,
        agent="monitor",
        type_="step",
        message="Starting monitoring cycle: Fetching alerts from Prometheus",
        data={"step": "fetch_alerts"},
    )

    alerts = get_prometheus_alerts()
    now = datetime.now(timezone.utc)

    _log_action(
        state,
        agent="monitor",
        type_="step",
        message=f"Retrieved {len(alerts)} alerts from Prometheus",
        data={"step": "alerts_received", "alert_count": len(alerts)},
    )

    if not alerts:
        if not state.last_normal_report_ts or (now - state.last_normal_report_ts).total_seconds() >= 300:
            _log_action(
                state,
                agent="monitor",
                type_="normal_report",
                message="System healthy. No active alerts.",
                data={"step": "normal_status"},
            )
            state.last_normal_report_ts = now
        return state

    for alert in alerts:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        alertname = labels.get("alertname", "unknown")
        incident_id = labels.get("incident_id", alertname)

        # Classification logic
        domain = "k8s" if "namespace" in labels or "pod" in labels else "network"
        classification_reason = (
            "Found 'namespace' or 'pod' label" if "namespace" in labels or "pod" in labels
            else "No k8s labels found, defaulting to network"
        )

        _log_action(
            state,
            agent="monitor",
            type_="step",
            message=f"Classifying alert '{alertname}': {classification_reason} → domain={domain}",
            data={"step": "classify", "alertname": alertname, "domain": domain, "reason": classification_reason},
        )

        existing = state.incidents.get(incident_id)
        if existing is None:
            _log_action(
                state,
                agent="monitor",
                type_="step",
                message=f"Creating new incident: {incident_id}",
                data={"step": "create_incident", "incident_id": incident_id},
            )
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
            _log_action(
                state,
                agent="monitor",
                type_="step",
                message=f"Updating existing incident: {incident_id}",
                data={"step": "update_incident", "incident_id": incident_id},
            )
            existing.updated_at = now
            existing.status = "new"

        _log_action(
            state,
            agent="monitor",
            type_="alert_received",
            message=f"Alert {alertname} classified as {domain}",
            data={"incident_id": incident_id, "labels": labels, "domain": domain},
        )

    _log_action(
        state,
        agent="monitor",
        type_="step",
        message=f"Monitoring cycle complete: Processed {len(alerts)} alerts",
        data={"step": "complete", "alerts_processed": len(alerts)},
    )

    return state


def k8s_node(state: GraphState) -> GraphState:
    """
    Kubernetes Agent: inspects K8s-related incidents.
    """
    k8s_incidents = [inc for inc in state.incidents.values() if inc.domain == "k8s" and inc.status == "new"]
    
    _log_action(
        state,
        agent="k8s",
        type_="step",
        message=f"K8s Agent starting: Found {len(k8s_incidents)} new k8s incidents to investigate",
        data={"step": "start", "incident_count": len(k8s_incidents)},
    )

    for incident in k8s_incidents:
        namespace = incident.labels.get("namespace", "default")
        pod_name = incident.labels.get("pod") or incident.labels.get("pod_name")
        
        if not pod_name:
            _log_action(
                state,
                agent="k8s",
                type_="step",
                message=f"Skipping incident {incident.id}: No pod name found in labels",
                data={"step": "skip", "incident_id": incident.id, "reason": "no_pod_name"},
            )
            continue

        _log_action(
            state,
            agent="k8s",
            type_="step",
            message=f"Investigating pod {namespace}/{pod_name} for incident {incident.id}",
            data={"step": "investigate", "incident_id": incident.id, "namespace": namespace, "pod": pod_name},
        )

        _log_action(
            state,
            agent="k8s",
            type_="step",
            message=f"Fetching pod status for {namespace}/{pod_name}",
            data={"step": "fetch_pod_status", "namespace": namespace, "pod": pod_name},
        )
        status = get_pod_status(namespace, pod_name)
        
        _log_action(
            state,
            agent="k8s",
            type_="step",
            message=f"Fetching pod events for {namespace}/{pod_name}",
            data={"step": "fetch_pod_events", "namespace": namespace, "pod": pod_name},
        )
        events = get_pod_events(namespace, pod_name)

        _log_action(
            state,
            agent="k8s",
            type_="step",
            message=f"Analyzing pod data: status={status.get('phase', 'unknown')}, events_count={len(events)}",
            data={"step": "analyze", "pod_status": status, "events_count": len(events)},
        )

        prompt = (
            "You are the Kubernetes incident analysis agent in an AIOps multi-agent monitoring system. "
            "Your task is to diagnose Kubernetes incidents using only the data provided and to produce a concise, "
            "expert-level explanation.\n\n"
            "Context:\n"
            f"- Incident (JSON): {incident.model_dump()}\n"
            f"- Pod status (JSON): {status}\n"
            "- Recent pod events (one per line):\n"
            + "\n".join(events)
            + "\n\n"
            "Instructions:\n"
            "1. Identify the most likely root cause of the problem.\n"
            "2. Cite the specific status fields or event messages that support your conclusion.\n"
            "3. In 3–6 sentences, summarize the root cause and its impact on the workload.\n"
            "4. Suggest one or two concrete, low-risk remediation steps an SRE could take next.\n"
            "5. Do not invent data that is not present in the inputs.\n"
            "6. Respond in plain English only (no JSON)."
        )
        
        _log_action(
            state,
            agent="k8s",
            type_="step",
            message="Calling LLM to generate root cause analysis and recommendations",
            data={"step": "llm_call", "incident_id": incident.id},
        )
        
        # Call LLM, but do not let failures crash the whole graph run.
        try:
            llm_response = ollama_llm.invoke(prompt)
            # Extract content from LLM response (handle both string and Message objects)
            if hasattr(llm_response, 'content'):
                summary = str(llm_response.content)
            elif hasattr(llm_response, 'text'):
                summary = str(llm_response.text)
            else:
                summary = str(llm_response)
            
            _log_action(
                state,
                agent="k8s",
                type_="step",
                message=f"LLM analysis complete: Generated {len(summary)} character recommendation",
                data={"step": "llm_success", "incident_id": incident.id, "summary_length": len(summary)},
            )
        except Exception as exc:  # noqa: BLE001
            summary = (
                "LLM error while generating Kubernetes incident summary. "
                f"Proceed with raw status/events only. Error: {exc}"
            )
            _log_action(
                state,
                agent="k8s",
                type_="step",
                message=f"LLM call failed: {exc}",
                data={"step": "llm_error", "incident_id": incident.id, "error": str(exc)},
            )

        incident.findings = {
            "pod_status": status,
            "events": events,
        }
        incident.recommendation = summary
        incident.assigned_agent = "k8s"
        incident.status = "investigating"
        incident.updated_at = datetime.now(timezone.utc)

        _log_action(
            state,
            agent="k8s",
            type_="investigation",
            message=f"Investigated pod {namespace}/{pod_name}: Status={status.get('phase', 'unknown')}, Root cause analysis complete",
            data={"incident_id": incident.id, "namespace": namespace, "pod": pod_name, "status": status},
        )

    _log_action(
        state,
        agent="k8s",
        type_="step",
        message=f"K8s Agent complete: Processed {len(k8s_incidents)} incidents",
        data={"step": "complete", "incidents_processed": len(k8s_incidents)},
    )

    return state


def network_node(state: GraphState) -> GraphState:
    """
    Network Agent: inspects network-related incidents.
    """
    network_incidents = [inc for inc in state.incidents.values() if inc.domain == "network" and inc.status == "new"]
    
    _log_action(
        state,
        agent="network",
        type_="step",
        message=f"Network Agent starting: Found {len(network_incidents)} new network incidents to investigate",
        data={"step": "start", "incident_count": len(network_incidents)},
    )

    for incident in network_incidents:
        device_id = incident.labels.get("device") or incident.labels.get("instance")
        interface_id = incident.labels.get("interface")

        if not device_id:
            _log_action(
                state,
                agent="network",
                type_="step",
                message=f"Skipping incident {incident.id}: No device ID found in labels",
                data={"step": "skip", "incident_id": incident.id, "reason": "no_device_id"},
            )
            continue

        _log_action(
            state,
            agent="network",
            type_="step",
            message=f"Investigating device {device_id} (interface={interface_id}) for incident {incident.id}",
            data={"step": "investigate", "incident_id": incident.id, "device_id": device_id, "interface_id": interface_id},
        )

        _log_action(
            state,
            agent="network",
            type_="step",
            message=f"Checking device status for {device_id}",
            data={"step": "check_device", "device_id": device_id},
        )
        device_status = check_device_status(device_id)
        
        interface_status = None
        if interface_id:
            _log_action(
                state,
                agent="network",
                type_="step",
                message=f"Checking interface {interface_id} status on device {device_id}",
                data={"step": "check_interface", "device_id": device_id, "interface_id": interface_id},
            )
            interface_status = check_interface_status(device_id, interface_id)

        _log_action(
            state,
            agent="network",
            type_="step",
            message=f"Device status: reachable={device_status.get('reachable', False)}, interface_status={interface_status is not None}",
            data={"step": "analyze", "device_status": device_status, "has_interface_status": interface_status is not None},
        )

        prompt = (
            "You are the Network incident analysis agent in an AIOps multi-agent monitoring system. "
            "Your task is to analyze network device and interface health using only the data provided and to produce "
            "a concise, expert-level explanation.\n\n"
            "Context:\n"
            f"- Incident (JSON): {incident.model_dump()}\n"
            f"- Device status (JSON): {device_status}\n"
            f"- Interface status (JSON or null): {interface_status}\n\n"
            "Instructions:\n"
            "1. Identify the most likely root cause of the issue (for example: device unreachable, interface down, "
            "errors on the link, misconfiguration).\n"
            "2. Cite the specific fields or text in the status data that support your conclusion.\n"
            "3. In 3–6 sentences, summarize the root cause and its potential impact on traffic.\n"
            "4. Suggest one or two concrete, low-risk remediation steps a network SRE could take next.\n"
            "5. Do not invent data that is not present in the inputs.\n"
            "6. Respond in plain English only (no JSON)."
        )
        
        _log_action(
            state,
            agent="network",
            type_="step",
            message="Calling LLM to generate root cause analysis and recommendations",
            data={"step": "llm_call", "incident_id": incident.id},
        )
        
        # Call LLM, but do not let failures crash the whole graph run.
        try:
            llm_response = ollama_llm.invoke(prompt)
            # Extract content from LLM response (handle both string and Message objects)
            if hasattr(llm_response, 'content'):
                summary = str(llm_response.content)
            elif hasattr(llm_response, 'text'):
                summary = str(llm_response.text)
            else:
                summary = str(llm_response)
            
            _log_action(
                state,
                agent="network",
                type_="step",
                message=f"LLM analysis complete: Generated {len(summary)} character recommendation",
                data={"step": "llm_success", "incident_id": incident.id, "summary_length": len(summary)},
            )
        except Exception as exc:  # noqa: BLE001
            summary = (
                "LLM error while generating network incident summary. "
                f"Proceed with raw device/interface status only. Error: {exc}"
            )
            _log_action(
                state,
                agent="network",
                type_="step",
                message=f"LLM call failed: {exc}",
                data={"step": "llm_error", "incident_id": incident.id, "error": str(exc)},
            )

        incident.findings = {
            "device_status": device_status,
            "interface_status": interface_status,
        }
        incident.recommendation = summary
        incident.assigned_agent = "network"
        incident.status = "investigating"
        incident.updated_at = datetime.now(timezone.utc)

        _log_action(
            state,
            agent="network",
            type_="investigation",
            message=f"Investigated device {device_id}: reachable={device_status.get('reachable', False)}, Root cause analysis complete",
            data={"incident_id": incident.id, "device_id": device_id, "device_status": device_status},
        )

    _log_action(
        state,
        agent="network",
        type_="step",
        message=f"Network Agent complete: Processed {len(network_incidents)} incidents",
        data={"step": "complete", "incidents_processed": len(network_incidents)},
    )

    return state


def review_node(state: GraphState) -> GraphState:
    """
    Review Agent:
    - Looks at incidents with findings.
    - Decides severity and whether to auto-remediate or escalate.
    """
    reviewable_incidents = [inc for inc in state.incidents.values() if inc.status in {"investigating", "new"}]
    
    _log_action(
        state,
        agent="review",
        type_="step",
        message=f"Review Agent starting: Evaluating {len(reviewable_incidents)} incidents for severity and remediation",
        data={"step": "start", "incident_count": len(reviewable_incidents)},
    )

    for incident in reviewable_incidents:
        findings = incident.findings or {}
        
        _log_action(
            state,
            agent="review",
            type_="step",
            message=f"Reviewing incident {incident.id}: domain={incident.domain}, has_findings={bool(findings)}",
            data={"step": "review_incident", "incident_id": incident.id, "domain": incident.domain},
        )

        prompt = (
            "You are the Review Agent in an AIOps multi-agent monitoring system. "
            "Given an incident and any findings from sub-agents, decide the severity and whether it is safe to "
            "auto-remediate in this lab/demo environment.\n\n"
            "Decision rules:\n"
            "- severity must be one of: \"low\", \"medium\", \"high\".\n"
            "- Use \"low\" only for clearly minor, low-impact issues with straightforward, reversible fixes.\n"
            "- Use \"high\" for issues that may cause or are causing outages, data loss, or major user impact; "
            "otherwise use \"medium\".\n"
            "- Set auto_remediate to true only for low-severity issues where the remediation is well-understood, "
            "reversible, and clearly safe in this environment.\n"
            "- If information is missing, contradictory, or risk is uncertain, set auto_remediate to false.\n\n"
            "Output format (required):\n"
            "Respond with a single JSON object on one line with exactly these keys: severity, auto_remediate, reason.\n"
            "- severity: one of \"low\", \"medium\", \"high\".\n"
            "- auto_remediate: a boolean.\n"
            "- reason: a short English explanation of why you chose this severity and remediation decision.\n\n"
            f"Incident: {incident.model_dump()}\n\nFindings: {findings}"
        )
        
        _log_action(
            state,
            agent="review",
            type_="step",
            message="Calling LLM to determine severity and auto-remediation decision",
            data={"step": "llm_call", "incident_id": incident.id},
        )
        
        # Call LLM, but do not let failures crash the whole graph run.
        try:
            llm_response = ollama_llm.invoke(prompt)
            # Extract content from LLM response
            if hasattr(llm_response, 'content'):
                raw = str(llm_response.content)
            elif hasattr(llm_response, 'text'):
                raw = str(llm_response.text)
            else:
                raw = str(llm_response)
        except Exception as exc:  # noqa: BLE001
            # Use a plain format string instead of f-string with JSON braces to avoid syntax issues.
            raw = '{{"severity": "unknown", "auto_remediate": false, "reason": "LLM error during review: {}"}}'.format(
                exc
            )
            _log_action(
                state,
                agent="review",
                type_="step",
                message=f"LLM call failed: {exc}",
                data={"step": "llm_error", "incident_id": incident.id, "error": str(exc)},
            )

        _log_action(
            state,
            agent="review",
            type_="step",
            message=f"Parsing LLM response: {raw[:100]}...",
            data={"step": "parse_response", "incident_id": incident.id, "raw_response": raw[:200]},
        )

        severity = "unknown"
        auto_remediate = False
        reason = "Failed to parse LLM response"
        try:
            import json

            parsed = json.loads(raw)
            severity = parsed.get("severity", "unknown")
            auto_remediate = bool(parsed.get("auto_remediate", False))
            reason = str(parsed.get("reason", "No reason provided"))
            
            _log_action(
                state,
                agent="review",
                type_="step",
                message=f"Decision: severity={severity}, auto_remediate={auto_remediate}, reason={reason[:50]}...",
                data={"step": "decision", "incident_id": incident.id, "severity": severity, "auto_remediate": auto_remediate, "reason": reason},
            )
        except Exception as e:
            _log_action(
                state,
                agent="review",
                type_="step",
                message=f"Failed to parse LLM JSON response: {e}",
                data={"step": "parse_error", "incident_id": incident.id, "error": str(e), "raw": raw[:200]},
            )
            severity = "unknown"
            auto_remediate = False

        incident.severity = severity

        if auto_remediate and incident.domain == "k8s":
            namespace = incident.labels.get("namespace", "default")
            pod_name = incident.labels.get("pod") or incident.labels.get("pod_name")
            if pod_name:
                _log_action(
                    state,
                    agent="review",
                    type_="step",
                    message=f"Auto-remediating: Restarting pod {namespace}/{pod_name}",
                    data={"step": "auto_remediate", "incident_id": incident.id, "namespace": namespace, "pod": pod_name},
                )
                restart_pod(namespace, pod_name)
                incident.auto_remediated = True
                incident.status = "auto_remediated"
                _log_action(
                    state,
                    agent="review",
                    type_="remediation",
                    message=f"Auto-restarted pod {namespace}/{pod_name}",
                    data={"incident_id": incident.id, "reason": reason},
                )
                continue

        if severity == "high" or not auto_remediate:
            _log_action(
                state,
                agent="review",
                type_="step",
                message=f"Escalating incident {incident.id}: severity={severity}, creating ticket",
                data={"step": "escalate", "incident_id": incident.id, "severity": severity},
            )
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
                message=f"Escalated incident {incident.id} with ticket {incident.ticket_id}: {reason}",
                data={"incident_id": incident.id, "ticket_id": incident.ticket_id, "reason": reason},
            )

        incident.updated_at = datetime.now(timezone.utc)

    _log_action(
        state,
        agent="review",
        type_="step",
        message=f"Review Agent complete: Processed {len(reviewable_incidents)} incidents",
        data={"step": "complete", "incidents_processed": len(reviewable_incidents)},
    )

    return state


def ticket_node(state: GraphState) -> GraphState:
    """
    Ticket Agent node.

    In this minimal implementation, the Review Agent already calls ticket tools
    directly, so this node is a no-op placeholder.
    """
    return state


