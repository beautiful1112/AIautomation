"""
Ticket and notification tools.

For now these are simple in-memory helpers suitable for a demo.
"""

from __future__ import annotations

from typing import Any, Dict, List


TICKETS: List[Dict[str, Any]] = []


def create_ticket(incident: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a simple in-memory ticket for an incident.
    """
    ticket_id = f"T-{incident.get('id', 'unknown')}"
    record = {
        "ticket_id": ticket_id,
        "incident": incident,
    }
    TICKETS.append(record)
    return {"ticket_id": ticket_id}


def notify_slack(channel: str, message: str) -> Dict[str, Any]:
    """
    Demo notification function that just returns a payload.
    """
    payload = {
        "channel": channel,
        "message": message,
    }
    # In a real system you would POST to Slack or another system here.
    return {"sent": True, "payload": payload}



