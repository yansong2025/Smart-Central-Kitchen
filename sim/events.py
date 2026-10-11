"""Demo events switched on and off from the sidebar "Demo Controls".

An event is a start time, plus an end time once it has been cleared.
Simulators call `is_active()`, `intensity()` or `active_seconds()` to react.
"""

import time

import numpy as np
import streamlit as st

# Add an entry here to get a new sidebar toggle under that system's name.
EVENTS = {
    "forming_jam": {"label": "Forming line jam", "system": "Dim Sum Forming Machine"},
    "defect_spike": {"label": "Defect spike (worn mould)", "system": "AI Quality Check"},
    "oven_door_leak": {"label": "Oven door seal leak", "system": "Smart Duck Oven"},
    "chiller_door_open": {"label": "Chiller door left open", "system": "IoT Temperature Monitoring"},
    "freezer_fault": {"label": "Freezer compressor fault", "system": "IoT Temperature Monitoring"},
    "amr_blocked": {"label": "Aisle blocked", "system": "AMR Robot"},
    "banquet_order": {"label": "Large banquet order", "system": "Demand Forecast"},
    "lunch_rush": {"label": "Lunch rush", "system": "FOH Service Robot"},
}


def alert(key, message, impact, action):
    """An alert as shown to the operator: what is wrong, what it costs, and what to do.

    `key` identifies the alert in the alert log while the wording changes (e.g. the temperature).
    """
    return {"key": key, "message": message, "impact": impact, "action": action}


def _events():
    return st.session_state.setdefault("events", {})


def trigger(key):
    now = time.time()
    _events()[key] = {"start": now, "end": None, "earlier_s": active_seconds(key, now)}


def clear(key):
    event = _events().get(key)
    if event is not None and event["end"] is None:
        event["end"] = time.time()


def clear_all():
    for key in _events():
        clear(key)


def is_active(key):
    event = _events().get(key)
    return event is not None and event["end"] is None


def active_seconds(key, now):
    """Total time event `key` has been switched on so far, across every trigger."""
    event = _events().get(key)
    if event is None:
        return 0.0
    return event["earlier_s"] + (event["end"] or now) - event["start"]


def intensity(key, t, ramp_s=30.0):
    """How strongly event `key` is felt at times `t` (epoch seconds), from 0 to 1.

    Ramps up towards 1 while the event is active, then fades back to 0 after
    it is cleared, so charts show a smooth excursion and recovery.
    """
    t = np.asarray(t, dtype=float)
    event = _events().get(key)
    if event is None:
        return np.zeros_like(t)

    start, end = event["start"], event["end"]
    rise = 1 - np.exp(-np.clip(t - start, 0, None) / ramp_s)
    if end is None:
        return rise

    peak = 1 - np.exp(-(end - start) / ramp_s)
    fade = peak * np.exp(-np.clip(t - end, 0, None) / ramp_s)
    return np.where(t <= end, rise, fade)
