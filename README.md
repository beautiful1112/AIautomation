Here’s a complete `README.md` you can drop into your repo. It combines high‑level architecture, low‑level design, and how everything fits together.

```markdown
# 🛰️ AIOps Multi-Agent Monitoring Demo (Prometheus + K8s + Network)

This project is a **minimal, end-to-end AIOps demo** that:

- Continuously monitors infrastructure using **Prometheus**
- Uses a **multi-agent system (LangGraph)** to analyze alerts
- Delegates investigations to specialized **Kubernetes** and **Network** agents
- Aggregates findings in a **Review** agent that:
  - Auto-remediates **low-severity** issues
  - Escalates **high-severity** issues to humans (tickets/notifications)
- Exposes everything via a simple **web dashboard** (React)

> Goal: a **working but minimal** system that feels like a real AIOps control plane, not a toy script.

---

## 🧭 1. System Overview

At a high level, the system looks like this:

```text
           ┌───────────────────────────────────────┐
           │            Infrastructure             │
           │                                       │
           │   Kubernetes Cluster    Network Devs  │
           │   (pods, nodes, etc.)   (switches)    │
           └───────────────┬─────────────┬────────┘
                           │             │
                           │ Metrics     │ Metrics
                           ▼             ▼
                    ┌─────────────────────────┐
                    │       Prometheus        │
                    │   + Alertmanager        │
                    └──────────────┬──────────┘
                                   │ Alerts API
                                   ▼
                      ┌────────────────────────┐
                      │   AIOps Agent System   │
                      │ (LangGraph + FastAPI)  │
                      ├────────────────────────┤
                      │ Monitoring Orchestrator│
                      │ K8s Agent              │
                      │ Network Agent          │
                      │ Review Agent           │
                      │ Ticket/Notify Adapter  │
                      └─────────────┬──────────┘
                                    │ REST API
                                    ▼
                           ┌─────────────────┐
                           │  Web Frontend   │
                           │   (React UI)    │
                           └─────────────────┘
```

Core features:

- **Continuous polling** of Prometheus for alerts
- **Silent analysis** during healthy periods, with **periodic “all good” reports**
- **Automatic routing**:
  - K8s-related alerts → **Kubernetes Agent**
  - Network-related alerts → **Network Agent**
- **Shared state** and **message passing** between agents
- **Auto-remediation** for low-risk issues
- **Ticketing / human notification** for severe issues
- **Dashboard UI** to visualize status, incidents, and agent activity

---

## 🧱 2. Architecture

### 2.1 Logical Components

| Component                  | Responsibility                                                                 |
|---------------------------|-------------------------------------------------------------------------------|
| **Prometheus + Alertmanager** | Collects metrics from infra, triggers alerts                                |
| **Monitoring Orchestrator Agent** | Periodically fetches alerts, classifies, dispatches to sub-agents           |
| **Kubernetes Agent**      | Investigates k8s-related incidents (pods, nodes, resources)                   |
| **Network Agent**         | Investigates network-related incidents (devices, interfaces)                  |
| **Review Agent**          | Aggregates findings, assigns severity, chooses auto-remediation vs human     |
| **Ticket/Notification Adapter** | Simple ticket store + Slack/email-like notifications (demo-level)         |
| **State Store**           | Keeps incidents, actions, last normal status, agent stats                    |
| **REST API (FastAPI)**    | Exposes data for the frontend (status, incidents, agents)                    |
| **Web Frontend (React)**  | Dashboard, incidents, detail view, agent activity                            |

### 2.2 Agent-Oriented View (LangGraph)

We model the agents as nodes in a **LangGraph stateful workflow**:

```text
        ┌─────────────────────────────────────────────┐
        │                 Graph State                 │
        │ incidents, actions, stats, last_normal_ts   │
        └───────────────┬────────────────────────────┘
                        │
                        ▼
                ┌──────────────┐
                │  monitor_node│  (Monitoring Orchestrator Agent)
                └───────┬──────┘
                        │
        ┌───────────────┼─────────────────────┐
        ▼               ▼                     ▼
┌────────────┐   ┌───────────────┐     ┌─────────────┐
│ k8s_node   │   │ network_node  │     │ review_node │
│ K8s Agent  │   │ Network Agent │     │ Review Agent│
└─────┬──────┘   └──────┬────────┘     └──────┬──────┘
      │                 │                   ┌─┴──────────────┐
      └──────────────┬──┴──────────────────► ticket_node     │
                     │                     │ Ticket/Notify   │
                     └─────────────────────┴─────────────────┘
```

Control flow:

1. `monitor_node` polls Prometheus.
2. For each alert:
   - Classifies as Kubernetes vs Network.
   - Creates or updates an **Incident** in state.
   - Routes work to `k8s_node` or `network_node`.
3. `k8s_node` / `network_node` investigate using tools (k8s API, SNMP/HTTP, etc.) and write findings.
4. `review_node`:
   - Reads findings.
   - Decides severity.
   - Runs safe auto-remediation tools if appropriate.
   - Otherwise calls `ticket_node` to log and “notify” humans.
5. Agents log actions into a shared **Action log** for UI.

---

## ⚙️ 3. Technology Stack

### 3.1 Backend

- **Python 3.11+**
- **LangGraph** + **LangChain**
  - Multi-agent orchestration and stateful workflows
- **FastAPI**
  - REST API for frontend
- **SQLite** (default) or Postgres
  - Persistence for incidents and actions
- **Prometheus HTTP API**
  - Source of alerts
- **Kubernetes Python client**
  - Investigating k8s incidents
- **Network tooling (pluggable)**
  - SNMP (e.g., `pysnmp`) or fake HTTP API for demo
- **LLM provider**
  - OpenAI GPT-4.1, or another model via LangChain

### 3.2 Frontend

- **React + TypeScript**
- **UI library**
  - Tailwind CSS + shadcn/ui, or Chakra UI, or Material UI
- **Routing**
  - React Router or Next.js (if you prefer)
- **Data fetching**
  - React Query (TanStack Query) recommended

---

## 🧩 4. Data & State Model (Low-Level Design)

### 4.1 Core Domain Types

#### Incident

Represents a single problem, rooted in one or more Prometheus alerts.

```ts
// Conceptual TypeScript shape (Python will mirror via Pydantic)
type Incident = {
  id: string;                  // UUID
  source: 'prometheus';
  alertname: string;
  domain: 'k8s' | 'network';
  severity: 'low' | 'medium' | 'high' | 'unknown';
  status: 'new' | 'investigating' | 'auto_remediated' | 'awaiting_human' | 'resolved';
  labels: Record<string, string>;
  annotations: Record<string, string>;
  createdAt: string;
  updatedAt: string;
  autoRemediated: boolean;
  assignedAgent: 'monitor' | 'k8s' | 'network' | 'review' | null;
  findings?: Record<string, any>;     // Structured result from sub-agents
  recommendation?: string;            // Human-readable summary from Review Agent
  ticketId?: string | null;           // If escalated
};
```

#### Action (Agent Activity)

Log of “what agents did” for a given incident.

```ts
type Action = {
  id: string;
  incidentId: string;
  agent: 'monitor' | 'k8s' | 'network' | 'review' | 'ticket';
  type: string;                  // e.g. "alert_received", "investigation", "remediation", "ticket_created"
  message: string;               // summary
  data?: Record<string, any>;    // extra structured info
  createdAt: string;
};
```

#### Agent Stats

Optional, for UI and observability.

```ts
type AgentStats = {
  agent: 'monitor' | 'k8s' | 'network' | 'review' | 'ticket';
  lastActiveAt: string | null;
  incidentsHandled: number;
  actionsPerformed: number;
  autoRemediations: number;
};
```

### 4.2 LangGraph State Model

LangGraph needs a single shared state object. In Python (Pydantic style):

```python
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel

class IncidentModel(BaseModel):
    id: str
    source: str
    alertname: str
    domain: str
    severity: str
    status: str
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
    agent: str
    type: str
    message: str
    data: Optional[Dict[str, Any]] = None
    created_at: datetime

class GraphState(BaseModel):
    incidents: Dict[str, IncidentModel]
    actions: List[ActionModel]
    last_normal_report_ts: Optional[datetime] = None
```

Agents read/write `GraphState` and also persist to DB via helper functions.

---

## 🧠 5. Agent Design (Low-Level)

Each agent is a **tool-using LLM** node in LangGraph with a specific prompt and set of tools.

### 5.1 Monitoring Orchestrator Agent (`monitor_node`)

**Responsibility:**

- Poll Prometheus alerts API.
- For **no alerts**:
  - If ≥ 5 minutes since `last_normal_report_ts`, generate a short “system healthy” summary and update timestamp.
- For **alerts**:
  - Classify each alert as `k8s` or `network`.
  - Create or update `Incident`s in state.
  - Log actions.
  - Route to appropriate sub-agent (K8s or Network).

**Tools:**

- `get_prometheus_alerts()`
  - Calls `/api/v1/alerts` on Prometheus.
- Optional: `get_metric_range(metric_name, labels, window)`

**Prompt (conceptual):**

> You are the Monitoring Orchestrator Agent.  
> Every time you run, you MUST:
> 1. Call `get_prometheus_alerts`.
> 2. If there are no active alerts:
>    - If it's been ≥ 5 minutes since `last_normal_report_ts`, write a "normal status" message and update that timestamp, and log an Action.
> 3. If there are alerts:
>    - For each alert: classify domain as `k8s` or `network` based on labels like `namespace`, `pod`, `job`, `device`, etc.
>    - Create or update an Incident in state.
>    - Log an Action summarizing the detection.
> 4. Mark incidents as `new` and assign them to the appropriate sub-agent.

Routing uses LangGraph’s control logic (e.g., `if incident.domain == 'k8s' → k8s_node`, etc.).

### 5.2 Kubernetes Agent (`k8s_node`)

**Responsibility:**

- Given a `k8s` incident:
  - Deep-dive into pods/nodes/events.
  - Suggest probable root cause and remediation.

**Tools:**

- `get_pod_status(namespace, pod_name)`
- `get_pod_events(namespace, pod_name)`
- `get_node_status(node_name)`
- Optional remediation (used by Review Agent, not directly by K8s Agent):
  - `restart_pod(namespace, pod_name)`

**Prompt (conceptual):**

> You are the Kubernetes SRE Agent.  
> For each incident related to Kubernetes:
> - Use the tools to investigate pod and node status.
> - Identify likely root cause (e.g., CrashLoopBackOff, OOMKilled, node not ready).
> - Produce a structured `findings` object and a concise summary for humans.
> - Do not perform remediation; only diagnose.

K8s Agent updates the Incident’s `findings` and logs an Investigation Action.

### 5.3 Network Agent (`network_node`)

**Responsibility:**

- Given a `network` incident:
  - Check device status, interface states, basic counters.
  - Suggest root cause (e.g., interface down, errors, device unreachable).

**Tools:**

- `check_device_status(device_id)`
- `check_interface_status(device_id, interface_id)`
- Optional remediation (via Review Agent):
  - `manipulate_interface(device_id, interface_id)` (for demo; up or change vlan)

**Prompt (conceptual):**

> You are the Network SRE Agent.  
> Use network tools to determine whether the device and interfaces are healthy.  
> Provide structured `findings` and a short summary.  
> Do not perform remediation; only diagnose.

### 5.4 Review Agent (`review_node`)

**Responsibility:**

- Aggregate findings from K8s/Network Agents.
- Decide severity: low, medium, high.
- Decide action:
  - If low severity and a known safe fix:
    - Call remediation tools (restart pod, bounce interface).
    - Mark `auto_remediated = true`.
    - Set incident status `auto_remediated` or `resolved` if appropriate.
  - If high severity or uncertain:
    - Call ticket/notify tools (create ticket, notify Slack/email).
    - Set incident status `awaiting_human`.

**Tools:**

- Remediation:
  - `restart_pod(namespace, pod_name)`
  - `bounce_interface(device_id, interface)`
- Ticket/Notification:
  - `create_ticket(incident)`
  - `notify_slack(channel, message)` or `notify_email(to, subject, body)`

**Prompt (conceptual):**

> You are the Review Agent.  
> For each incident with completed findings:
> - Evaluate impact and confidence in the findings.
> - Choose a severity level.
> - If low severity and a single, well-understood fix is available, perform auto-remediation via tools.
> - Otherwise, create a ticket and produce clear human-facing recommendations.
> - Log all decisions and actions.

### 5.5 Ticket / Notification Agent (`ticket_node`)

**Responsibility:**

- Abstracts ticket creation and human notification.

**Tools:**

- Under the hood, can write to SQLite and optionally send a HTTP request to a Slack webhook.

---

## 🔌 6. Tools Design (Implementation-Level)

For the MVP, tools are **plain Python functions** wrapped as LangChain/LangGraph tools. No MCP yet (to keep it simple).

### 6.1 Prometheus Tools

```python
import requests

PROMETHEUS_URL = "http://192.168.229.143:9090"

def get_prometheus_alerts():
    resp = requests.get(f"{PROMETHEUS_URL}/api/v1/alerts", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["alerts"]
```

### 6.2 Kubernetes Tools

Using `kubernetes` Python client:

```python
from kubernetes import client, config

# Initialize config (in-cluster or from kubeconfig)
config.load_incluster_config()  # or load_kube_config()

core_api = client.CoreV1Api()

def get_pod_status(namespace: str, pod_name: str):
    pod = core_api.read_namespaced_pod(pod_name, namespace)
    return {
        "phase": pod.status.phase,
        "conditions": [c.type for c in (pod.status.conditions or [])],
        "container_statuses": [
            {
                "name": cs.name,
                "restart_count": cs.restart_count,
                "state": cs.state.to_dict(),
            }
            for cs in (pod.status.container_statuses or [])
        ],
    }

def get_pod_events(namespace: str, pod_name: str):
    field_selector = f"involvedObject.kind=Pod,involvedObject.name={pod_name}"
    events = core_api.list_namespaced_event(namespace, field_selector=field_selector)
    return [e.message for e in events.items]

def restart_pod(namespace: str, pod_name: str):
    core_api.delete_namespaced_pod(pod_name, namespace)
    return {"status": "deleted_for_restart"}
```


### 6.3 Network Tools (Demo-Friendly with Netmiko)



We implement three core tools:

- `check_device_status(device_id)`
- `check_interface_status(device_id, interface_id)`
- `manipulate_interface(device_id, interface_id)` *(up or change vlan)*

These tools:

1. Look up device connection details from a simple in-memory registry (or from config).
2. Use Netmiko to open an SSH session.
3. Run vendor-appropriate commands (e.g. Cisco IOS show commands).
4. Parse output into a **structured JSON-like dict** that agents can reason about.

> For a real environment, you’d likely:
> - Store credentials securely (Vault, env variables, etc.).
> - Use more robust parsing (TextFSM, Genie, TTP) instead of naive string parsing.

#### 6.3.1 Device registry

We keep a minimal device registry in Python. In a production system, this would be a CMDB or inventory database.

```python
# network_devices.py

from typing import Dict

# For demo: small, hardcoded inventory.
# In real usage, load from env, YAML, or DB.
NETWORK_DEVICES: Dict[str, dict] = {
    "lab-switch-1": {
        "device_type": "cisco_ios",
        "host": "10.0.0.11",
        "username": "admin",
        "password": "admin123",
        "port": 22,
    },
    "lab-switch-2": {
        "device_type": "cisco_ios",
        "host": "10.0.0.12",
        "username": "admin",
        "password": "admin123",
        "port": 22,
    },
    # Add more devices as needed
}

def get_device_params(device_id: str) -> dict:
    """
    Return Netmiko connection params for a given device_id.
    Raises KeyError if device is unknown.
    """
    if device_id not in NETWORK_DEVICES:
        raise KeyError(f"Unknown device_id: {device_id}")
    return NETWORK_DEVICES[device_id]
```

#### 6.3.2 Connecting with Netmiko

We define a small helper to establish a connection and handle cleanup.

```python
# netmiko_tools.py

from contextlib import contextmanager
from typing import Dict, Any
from netmiko import ConnectHandler
from .network_devices import get_device_params

@contextmanager
def netmiko_connection(device_id: str):
    """
    Context manager to open/close a Netmiko SSH connection.
    """
    params = get_device_params(device_id)
    conn = ConnectHandler(**params)
    try:
        yield conn
    finally:
        conn.disconnect()
```

#### 6.3.3 `check_device_status(device_id)`

This tool checks basic device reachability and some overall health information.

For a Cisco IOS switch, we might:

- Run `show version` → get hostname, model, uptime
- Optionally run `show ip interface brief` to ensure management interfaces are up

```python
# netmiko_tools.py (continued)

def check_device_status(device_id: str) -> Dict[str, Any]:
    """
    Check basic device health and reachability using Netmiko.
    """
    result: Dict[str, Any] = {
        "device_id": device_id,
        "reachable": False,
        "hostname": None,
        "model": None,
        "uptime": None,
        "raw": {},
    }

    try:
        with netmiko_connection(device_id) as conn:
            # Example: 'show version' for Cisco IOS
            output = conn.send_command("show version", use_textfsm=True)
            # If TextFSM templates are available, output may already be structured
            result["raw"]["show_version"] = output

            # Try to extract some structured info.
            # This will vary by vendor and whether TextFSM is configured.
            if isinstance(output, list) and output:
                # TextFSM structured output (list of dicts)
                first = output[0]
                result["hostname"] = first.get("hostname")
                result["model"] = first.get("hardware", [None])[0]
                result["uptime"] = first.get("uptime")
            else:
                # Fallback: simple string
                # In a real system, you'd parse more carefully or rely on TextFSM/Genie.
                result["hostname"] = None
                result["model"] = None
                result["uptime"] = None

            result["reachable"] = True

    except Exception as e:
        # On failure, reachable stays False, and we record the error.
        result["error"] = str(e)

    return result
```

> Note: `use_textfsm=True` requires TextFSM templates to be present; if not, you’ll get plain text and can either:
> - Turn off `use_textfsm`, or
> - Add templates for your device type.

#### 6.3.4 `check_interface_status(device_id, interface_id)`

This tool checks whether a specific interface is up/down and its line protocol status.

For Cisco IOS:

- Command: `show interface <interface_id>`
- Parse for:
  - “line protocol is up/down”
  - “is up/down”

```python
def check_interface_status(device_id: str, interface_id: str) -> Dict[str, Any]:
    """
    Check the operational status of a given interface.
    """
    result: Dict[str, Any] = {
        "device_id": device_id,
        "interface_id": interface_id,
        "reachable": False,
        "admin_status": None,
        "oper_status": None,
        "description": None,
        "raw": {},
    }

    try:
        with netmiko_connection(device_id) as conn:
            cmd = f"show interface {interface_id}"
            output = conn.send_command(cmd)
            result["raw"]["show_interface"] = output
            result["reachable"] = True

            # Naive parsing example for Cisco IOS-style output.
            # Example first line: "GigabitEthernet0/1 is up, line protocol is up"
            first_line = output.splitlines()[0] if output else ""
            line_lower = first_line.lower()

            if "is administratively down" in line_lower:
                result["admin_status"] = "down"
            elif "is up" in line_lower or "up," in line_lower:
                result["admin_status"] = "up"
            else:
                result["admin_status"] = "unknown"

            if "line protocol is up" in line_lower:
                result["oper_status"] = "up"
            elif "line protocol is down" in line_lower:
                result["oper_status"] = "down"
            else:
                result["oper_status"] = "unknown"

            # Optional: parse description from later lines.
            for line in output.splitlines():
                if "Description:" in line:
                    result["description"] = line.split("Description:", 1)[1].strip()
                    break

    except Exception as e:
        result["error"] = str(e)

    return result
```

In a more robust implementation, you would:

- Use `send_command("show interfaces", use_textfsm=True)` and filter by interface name.
- Or use Cisco Genie / pyATS for structured parsing.

#### 6.3.5 `bounce_interface(device_id, interface_id)` (Optional, Auto-Remediation)

This tool **administratively disables and then re-enables** an interface. It’s powerful and potentially disruptive, so:

- Only use in **safe test environments**.
- Only call from the **Review Agent** with strict conditions (e.g., low severity, specific interface, lab sandbox).

For Cisco IOS, we might:

- Enter config mode
- Run:
  - `interface <interface_id>`
  - `shutdown`
  - wait a few seconds
  - `no shutdown`

```python
import time

def bounce_interface(device_id: str, interface_id: str) -> Dict[str, Any]:
    """
    Disable and re-enable an interface using Netmiko.
    USE ONLY IN SAFE LAB ENVIRONMENTS.
    """
    result: Dict[str, Any] = {
        "device_id": device_id,
        "interface_id": interface_id,
        "success": False,
        "steps": [],
    }

    try:
        with netmiko_connection(device_id) as conn:
            commands = [
                f"interface {interface_id}",
                "shutdown",
            ]
            output1 = conn.send_config_set(commands)
            result["steps"].append({"cmds": commands, "output": output1})

            time.sleep(2)  # small pause

            commands2 = [
                f"interface {interface_id}",
                "no shutdown",
            ]
            output2 = conn.send_config_set(commands2)
            result["steps"].append({"cmds": commands2, "output": output2})

            result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result
```

#### 6.3.6 Exposing Netmiko Tools to the Network Agent

In your LangGraph / LangChain setup, you expose these Python functions as tools for the **Network Agent**:

```python
from langchain.tools import tool
from .netmiko_tools import (
    check_device_status,
    check_interface_status,
    bounce_interface,
)

@tool("check_device_status", return_direct=False)
def check_device_status_tool(device_id: str):
    """Check basic health and reachability of a network device via SSH."""
    return check_device_status(device_id)

@tool("check_interface_status", return_direct=False)
def check_interface_status_tool(device_id: str, interface_id: str):
    """Check operational status of a device interface (up/down)."""
    return check_interface_status(device_id, interface_id)

@tool("bounce_interface", return_direct=False)
def bounce_interface_tool(device_id: str, interface_id: str):
    """
    Disable and re-enable an interface. DANGEROUS: use only in lab or with explicit safeguards.
    """
    return bounce_interface(device_id, interface_id)
```

The **Network Agent** will be configured with these tools, and in its prompt you explain:

- It should use `check_device_status` and `check_interface_status` to diagnose.
- It should **not** call `bounce_interface` directly for remediation; that is reserved for the Review Agent (for safety).



### 6.4 Ticket / Notification Tools

```python
# Simplified example, actual implementation uses DB and HTTP

def create_ticket(incident):
    # Insert into DB and return ticket_id
    ticket_id = f"T-{incident.id}"
    # ... DB insert ...
    return {"ticket_id": ticket_id}

def notify_slack(channel: str, message: str):
    # POST to Slack webhook (configured securely)
    # This can be a no-op or simple print for demo
    print(f"[SLACK] Channel={channel} Message={message}")
    return {"sent": True}
```

---

## 🌐 7. REST API for Frontend

The backend exposes read-only APIs for the React UI. (All “write” operations come from agents, not from the UI, in the minimal demo.)

### 7.1 Endpoints

1. `GET /api/status`

Returns summary for dashboard:

```json
{
  "overall_status": "healthy",
  "last_normal_report": {
    "text": "Cluster healthy. No active alerts.",
    "timestamp": "2025-01-01T10:00:00Z"
  },
  "stats": {
    "active_incidents": 1,
    "k8s_incidents": 1,
    "network_incidents": 0,
    "auto_remediations_24h": 3
  }
}
```

2. `GET /api/incidents`

Query params: `severity`, `domain`, `status`, `search`.

Returns a list of incidents with basic info.

3. `GET /api/incidents/:id`

Returns full incident data including timeline of actions:

```json
{
  "incident": { /* IncidentModel serialized */ },
  "actions": [ /* list of ActionModel for this incident */ ]
}
```

4. `GET /api/agents`

Returns agent stats:

```json
[
  {
    "agent": "monitor",
    "lastActiveAt": "2025-01-01T10:03:00Z",
    "incidentsHandled": 10,
    "actionsPerformed": 100,
    "autoRemediations": 0
  },
  ...
]
```

5. `GET /api/agents/:agent/activity`

Returns recent actions taken by one agent.

---

## 🖥️ 8. Frontend Pages (UI Design)

### 8.1 Pages Overview

- `/` – **Dashboard**
- `/incidents` – **Incidents List**
- `/incidents/:id` – **Incident Detail**
- `/agents` – **Agents Activity** (optional)

### 8.2 Dashboard

Sections:

1. **Global Health Banner**
   - `overall_status` (Healthy / Degraded)
   - `last_normal_report.text` & timestamp

2. **Summary Cards**
   - Active incidents
   - K8s incidents
   - Network incidents
   - Auto-remediations in last 24h

3. **Active Incidents Preview**
   - Table of top N incidents (ID, domain, severity, summary, status)

4. **Recent Agent Activity**
   - Stream of recent `Action`s (agent name + message + timestamp)

### 8.3 Incidents List (`/incidents`)

- Filters:
  - Domain (All / K8s / Network)
  - Severity (All / Low / Medium / High)
  - Status (Active / Resolved / Awaiting human / Auto-remediated)
  - Text search
- Table:
  - Incident ID
  - Domain
  - Severity (colored badge)
  - Status
  - Summary
  - Created at
  - Last updated

Click row → `/incidents/:id`.

### 8.4 Incident Detail (`/incidents/:id`)

- Header:
  - Incident ID
  - Domain
  - Severity
  - Status
- Left:
  - Original Prometheus alert (labels, annotations)
  - Timestamps
- Right:
  - **Timeline** of actions:
    - Monitoring Orchestrator: alerts observed
    - K8s Agent / Network Agent: diagnostic steps
    - Review Agent: severity & decisions
    - Ticket Agent: ticket creation
  - **Auto-remediation panel**:
    - Did we auto-remediate?
    - What was executed?
    - Result

### 8.5 Agents Page (`/agents`)

- For each agent:
  - Name, role description
  - Status (last active at)
  - Stats (incidents handled, actions, auto-remediations)
  - Recent actions list

---

## 🚀 9. Running the System

> This section is a template; you’ll adapt the exact commands to your environment.

### 9.1 Prerequisites

- Python 3.11+
- Node.js (for frontend)
- A running:
  - **Prometheus** reachable at `http://192.168.229.143:9090` (with `kube-state-metrics` & network exporter)
  - **Kubernetes cluster** (kind/k3s/managed)
  - Optional **network device simulator**

### 9.2 Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

pip install -r requirements.txt

# Start FastAPI + LangGraph runner (uvicorn example):
uvicorn app:app --reload
```

The LangGraph loop can be run:

- As part of the FastAPI startup event, or
- As a separate background worker process.

### 9.3 Frontend

```bash
cd frontend
npm install
npm run dev   # or npm run start (depending on your setup)
```

Visit `http://localhost:3000` (or your port) to view the dashboard.

---

## 🧪 10. Testing the Demo

1. **Healthy state**
   - Ensure no alerts in Prometheus.
   - Wait > 5 minutes.
   - Dashboard should show:
     - Status: Healthy
     - Last normal report message from Monitoring Orchestrator.

2. **K8s incident**
   - Deploy a pod that crashes or force a CrashLoopBackOff.
   - Confirm alert is firing in Prometheus (e.g. `KubePodCrashLooping`).
   - Observe:
     - New incident appears.
     - K8s Agent performs investigation.
     - Review Agent classifies severity.
     - Auto-remediation may restart the pod if allowed.
     - Timeline on Incident Detail shows all steps.

3. **Network incident**
   - Simulate a device or interface down (or use your lab).
   - Confirm network alert.
   - Network Agent investigates, Review Agent responds accordingly.

---

## 🧩 11. Future Improvements

- Introduce **MCP**-based tools instead of local Python tools for reusable multi-process tooling.
- Add more specialized agents:
  - Capacity planning agent
  - Log analysis agent (ELK / Loki integration)
- Add **Grafana** links / embedded panels for metrics visualization.
- Implement proper **authentication & RBAC** in the UI.
- Use streaming / WebSockets for real-time updates instead of polling.

---
---

## 🧠 LLM Configuration (Ollama + qwen-20b)

This project uses a **local LLM** served by **Ollama**, specifically the `qwen-20b` model.

- Ensure Ollama is installed and running on the backend host.
- Pull and prepare the model:

ollama pull qwen:20b- In the backend, agents will use the Ollama HTTP API (typically `http://localhost:11434`) via LangChain’s Ollama integration, for example:

from langchain_community.llms import Ollama

llm = Ollama(model="qwen:20b", base_url="http://localhost:11434")You can adjust the `model` name or `base_url` if your Ollama setup differs.
## 📌 Summary

This project demonstrates:

- A **multi-agent AIOps architecture** using LangGraph.
- Deep integration with **Prometheus**, **Kubernetes**, and **network devices**.
- A **minimal but powerful frontend dashboard** that makes the agents’ work visible.
- A clear separation between:
  - **Domain tools** (Prometheus, k8s, network, tickets)
  - **Agent logic** (monitoring, k8s, network, review)
  - **UI** (React dashboard)

The design is intentionally minimal but extensible, so you can evolve it into a more complex production setup over time.
```