"""The 3D digital twins: the kitchen, and the restaurant dining room.

Python decides everything a twin shows (zones, labels, alerts, robot position)
and sends it as plain data. twin/kitchen.js only draws it.
"""

from pathlib import Path

import streamlit as st

from sim import amr, events, foh_robot, layout, systems, temperature

_draw = st.components.v2.component("kitchen_twin", js=(Path(__file__).parent / "kitchen.js").read_text())

PAGES = {system["name"]: system["page"] for system in systems.SYSTEMS}


def click_targets():
    """Which page opens when a zone (or the robot) is clicked on the twin."""
    targets = {amr.NAME: PAGES["AMR Robot"]}
    for sensor in temperature.SENSORS:
        targets[sensor["name"]] = PAGES["IoT Temperature Monitoring"]
    for zone in layout.ZONES:
        if "system" in zone:
            targets[zone["name"]] = PAGES[zone["system"]]
    return targets


def kitchen_state(now):
    """What every zone and the robot look like right now."""
    sensors = {s["name"]: s for s in temperature.latest(now)}
    cards = {c["name"]: c for c in systems.summary(now)}
    targets = click_targets()

    zones = []
    for zone in layout.ZONES:
        label, alert, door_open = "", False, False
        if zone["name"] in sensors:
            sensor = sensors[zone["name"]]
            label = f"{sensor['temp_c']:.1f} °C"
            alert = not sensor["ok"]
            door_open = sensor.get("event") == "chiller_door_open" and events.is_active("chiller_door_open")
        elif "system" in zone:
            card = cards[zone["system"]]
            label = card["value"]
            alert = bool(card["alerts"])
        zones.append({**zone, "label": label, "alert": alert, "busy": False, "door_open": door_open,
                      "clickable": zone["name"] in targets})

    robot = amr.state(now)
    return {
        "floor": layout.FLOOR,
        "zones": zones,
        "safety_zones": [
            {"x": 5.9, "z": -5.5, "w": 4.2, "d": 4.6, "color": 0xd03b3b},
            {"x": -0.4, "z": 5.5, "w": 6.4, "d": 4.6, "color": 0xd03b3b},
            {"x": 0, "z": 0, "w": 26, "d": 5.6, "color": 0xe6a12c},
            {"x": -4.45, "z": -5.5, "w": 15.7, "d": 4.6, "color": 0x2a78d6},
            {"x": 10.2, "z": -5.5, "w": 3.8, "d": 4.6, "color": 0x2a78d6},
        ],
        "route": [[x, z] for x, z, _, _ in layout.AMR_ROUTE],
        "amr": {"name": amr.NAME, "kind": "amr", "x": robot["x"], "z": robot["z"], "blocked": robot["blocked"],
                "label": "", "carrying": True, "clickable": True},
    }


def dining_state(now):
    """The restaurant dining room: tables, the kitchen pass and the service robot."""
    # The simulator measures from the kitchen pass; the twin is centred on the room.
    def place(spot):
        return {"x": spot["x"] - 5.25, "z": spot["y"] - 3.5}

    orders = foh_robot.queue(now)
    waiting = {order["Table"] for order in orders}
    zones = [{
        "name": "Kitchen pass", "kind": "pass", **place(foh_robot.KITCHEN_PASS), "w": 1.6, "d": 4.0,
        "label": f"{len(orders)} orders waiting", "alert": bool(foh_robot.status(now)["alerts"]),
        "busy": False, "door_open": False, "clickable": False,
    }]
    for table in foh_robot.TABLES:
        is_waiting = table["table"] in waiting
        zones.append({
            "name": f"T{table['table']}", "kind": "table", **place(table), "w": 2.3, "d": 2.3,
            "guests": table["guests"], "label": "Order waiting" if is_waiting else "",
            "alert": False, "busy": is_waiting, "served": not is_waiting, "door_open": False, "clickable": False,
        })

    robot = foh_robot.position(now)
    return {
        "floor": {"width": 13.5, "depth": 9.0, "color": "#e9dcc6"},
        "zones": zones,
        "safety_zones": [
            {"x": 0, "z": 0, "w": 13.0, "d": 4.2, "color": 0xe6a12c},
        ],
        "route": [],
        "amr": {"name": foh_robot.NAME, "kind": "server", **place(robot), "blocked": False,
                "label": robot["short"], "carrying": robot["carrying"], "clickable": False},
    }


def dining_twin(now, height=460):
    """Draw the dining-room twin for the FOH Service Robot page."""
    state = {**dining_state(now), "focus": "dining", "height": height,
             "safety_zones_visible": st.session_state.get("safety_zones", False)}
    _draw(data=state, key="dining_twin", height=height, on_clicked_change=lambda: None)


def kitchen_twin(now, focus="overview", height=460):
    """Draw the kitchen twin. `focus` picks the starting camera:
    "overview", "cold_rooms", "amr", "forming" or "oven".

    Clicking a zone or the robot opens the page of the system behind it.
    """
    state = {**kitchen_state(now), "focus": focus, "height": height,
             "safety_zones_visible": st.session_state.get("safety_zones", False)}
    result = _draw(data=state, key="kitchen_twin", height=height, on_clicked_change=lambda: None)
    page = click_targets().get(result.clicked)
    if page:
        # The twin sits inside an auto-refreshing fragment, so hand the request
        # to app.py, which switches page on a full rerun.
        st.session_state["open_page"] = page
        st.rerun()
