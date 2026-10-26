"""A log of every alert in this session: when it was raised, acknowledged and resolved.

Simulators only say which alerts are active right now. This module remembers
them, so an operator can acknowledge an alert and the Overview can show a history.
"""

import time
from datetime import datetime

import streamlit as st


def _log():
    return st.session_state.setdefault("alert_log", [])


def _open_record(key):
    """The unresolved log entry for alert `key`, if there is one."""
    for record in reversed(_log()):
        if record["key"] == key and record["resolved"] is None:
            return record
    return None


def update(cards, now):
    """Compare the log with the alerts active now (`cards` from `systems.summary`)."""
    active = {alert["key"]: (card["name"], alert) for card in cards for alert in card["alerts"]}
    for key, (system, alert) in active.items():
        if _open_record(key) is None:
            _log().append({"key": key, "system": system, "message": alert["message"],
                           "raised": now, "acknowledged": None, "resolved": None})
    for record in _log():
        if record["resolved"] is None and record["key"] not in active:
            record["resolved"] = now


def acknowledge(key):
    record = _open_record(key)
    if record is not None and record["acknowledged"] is None:
        record["acknowledged"] = time.time()


def is_logged(key):
    return _open_record(key) is not None


def raised_at(key):
    """Time the open alert `key` was raised, or None if the log has not seen it yet."""
    record = _open_record(key)
    return record["raised"] if record else None


def acknowledged_at(key):
    """Time the open alert `key` was acknowledged, or None."""
    record = _open_record(key)
    return record["acknowledged"] if record else None


def clock_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%H:%M:%S") if timestamp else "—"


def table():
    """The log as rows for display, newest first."""
    rows = []
    for record in reversed(_log()):
        if record["resolved"]:
            status = "Resolved"
        elif record["acknowledged"]:
            status = "Acknowledged"
        else:
            status = "Open"
        acknowledged = "—"
        if record["acknowledged"]:
            acknowledged = f"{clock_time(record['acknowledged'])} (after {record['acknowledged'] - record['raised']:.0f} s)"
        rows.append({
            "Raised": clock_time(record["raised"]),
            "System": record["system"],
            "Alert": record["message"],
            "Status": status,
            "Acknowledged": acknowledged,
            "Resolved": clock_time(record["resolved"]),
        })
    return rows
