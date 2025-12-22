"""
Kubernetes tools used by the Kubernetes Agent and Review Agent.

These functions are thin wrappers around the kubernetes Python client.
"""

from __future__ import annotations

from typing import Any, Dict, List, cast

from kubernetes import client, config


def _load_config() -> None:
    """
    Load Kubernetes configuration.

    Tries in-cluster config first, then falls back to local kubeconfig.
    """
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()


def get_pod_status(namespace: str, pod_name: str) -> Dict[str, Any]:
    """
    Return basic status information for a pod.
    """
    _load_config()
    core_api = client.CoreV1Api()
    pod = core_api.read_namespaced_pod(pod_name, namespace)
    
    # Type assertion: read_namespaced_pod returns V1Pod, not None
    pod_obj = cast(Any, pod)
    
    if pod_obj is None or not hasattr(pod_obj, "status") or pod_obj.status is None:
        return {
            "phase": "Unknown",
            "conditions": [],
            "container_statuses": [],
        }
    
    return {
        "phase": pod_obj.status.phase,
        "conditions": [c.type for c in (pod_obj.status.conditions or [])],
        "container_statuses": [
            {
                "name": cs.name,
                "restart_count": cs.restart_count,
                "state": cs.state.to_dict(),
            }
            for cs in (pod_obj.status.container_statuses or [])
        ],
    }


def get_pod_events(namespace: str, pod_name: str) -> List[str]:
    """
    Return recent event messages for a pod.
    """
    _load_config()
    core_api = client.CoreV1Api()
    field_selector = f"involvedObject.kind=Pod,involvedObject.name={pod_name}"
    events = core_api.list_namespaced_event(namespace, field_selector=field_selector)
    return [e.message for e in events.items]


def restart_pod(namespace: str, pod_name: str) -> Dict[str, Any]:
    """
    Delete a pod so that its controller can recreate it.
    """
    _load_config()
    core_api = client.CoreV1Api()
    core_api.delete_namespaced_pod(pod_name, namespace)
    return {"status": "deleted_for_restart", "namespace": namespace, "pod": pod_name}



