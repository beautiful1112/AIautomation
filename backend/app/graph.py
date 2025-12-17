"""
LangGraph workflow wiring together the agents defined in agents.py.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from .agents import k8s_node, monitor_node, network_node, review_node, ticket_node
from .models import GraphState


def build_graph():
    """
    Build and return a compiled LangGraph workflow.
    """
    workflow = StateGraph(GraphState)

    workflow.add_node("monitor", monitor_node)
    workflow.add_node("k8s", k8s_node)
    workflow.add_node("network", network_node)
    workflow.add_node("review", review_node)
    workflow.add_node("ticket", ticket_node)

    # Simple linear flow for now: monitor -> k8s -> network -> review -> ticket -> END.
    # You can replace this later with conditional routing based on incident domain.
    workflow.set_entry_point("monitor")
    workflow.add_edge("monitor", "k8s")
    workflow.add_edge("k8s", "network")
    workflow.add_edge("network", "review")
    workflow.add_edge("review", "ticket")
    workflow.add_edge("ticket", END)

    return workflow.compile()


