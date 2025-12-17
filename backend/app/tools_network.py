"""
Network tools for interacting with lab routers and switches using Netmiko.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict

from netmiko import ConnectHandler


# Simple in-memory device registry for the lab.
# You should adjust host, username and password for your EVE-NG devices.
NETWORK_DEVICES: Dict[str, Dict[str, Any]] = {
    "lab-router-1": {
        "device_type": "cisco_ios",
        "host": "10.0.0.11",
        "username": "admin",
        "password": "admin123",
        "port": 22,
    },
    "lab-router-2": {
        "device_type": "cisco_ios",
        "host": "10.0.0.12",
        "username": "admin",
        "password": "admin123",
        "port": 22,
    },
    "lab-switch-1": {
        "device_type": "cisco_ios",
        "host": "10.0.0.21",
        "username": "admin",
        "password": "admin123",
        "port": 22,
    },
    "lab-switch-2": {
        "device_type": "cisco_ios",
        "host": "10.0.0.22",
        "username": "admin",
        "password": "admin123",
        "port": 22,
    },
    "lab-switch-3": {
        "device_type": "cisco_ios",
        "host": "10.0.0.23",
        "username": "admin",
        "password": "admin123",
        "port": 22,
    },
}


def get_device_params(device_id: str) -> Dict[str, Any]:
    """
    Return Netmiko connection parameters for a given device id.
    """
    if device_id not in NETWORK_DEVICES:
        raise KeyError(f"Unknown device_id: {device_id}")
    return NETWORK_DEVICES[device_id]


@contextmanager
def netmiko_connection(device_id: str):
    """
    Context manager to open and close a Netmiko SSH connection.
    """
    params = get_device_params(device_id)
    conn = ConnectHandler(**params)
    try:
        yield conn
    finally:
        conn.disconnect()


def check_device_status(device_id: str) -> Dict[str, Any]:
    """
    Check basic device reachability and gather simple information.
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
            output = conn.send_command("show version", use_textfsm=True)
            result["raw"]["show_version"] = output

            if isinstance(output, list) and output:
                first = output[0]
                result["hostname"] = first.get("hostname")
                hardware = first.get("hardware") or []
                result["model"] = hardware[0] if hardware else None
                result["uptime"] = first.get("uptime")

            result["reachable"] = True
    except Exception as exc:
        result["error"] = str(exc)

    return result


def check_interface_status(device_id: str, interface_id: str) -> Dict[str, Any]:
    """
    Check administrative and operational status of a network interface.
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

            first_line = output.splitlines()[0] if output else ""
            line_lower = first_line.lower()

            if "is administratively down" in line_lower:
                result["admin_status"] = "down"
            elif " is up" in line_lower or "up," in line_lower:
                result["admin_status"] = "up"
            else:
                result["admin_status"] = "unknown"

            if "line protocol is up" in line_lower:
                result["oper_status"] = "up"
            elif "line protocol is down" in line_lower:
                result["oper_status"] = "down"
            else:
                result["oper_status"] = "unknown"

            for line in output.splitlines():
                if "Description:" in line:
                    result["description"] = line.split("Description:", 1)[1].strip()
                    break
    except Exception as exc:
        result["error"] = str(exc)

    return result



