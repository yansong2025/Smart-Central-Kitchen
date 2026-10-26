"""The 3D digital twins: the kitchen, and the restaurant dining room.

Python decides everything a twin shows (zones, labels, alerts, robot position)
and sends it as plain data. twin/kitchen.js only draws it.

The twin is also the main demo control: clicking a machine opens an inspector
panel in the 3D view with buttons to simulate its fault or open its page.
"""

from pathlib import Path

import streamlit as st

from sim import amr, duck_oven, events, foh_robot, forming, layout, quality, systems, temperature

_HERE = Path(__file__).parent
# models.js (the detailed 3D models) is joined in front of kitchen.js (the scene and its controls).
_draw = st.components.v2.component(
    "kitchen_twin",
    js=(_HERE / "models.js").read_text() + "\n" + (_HERE / "kitchen.js").read_text(),
    css=(_HERE / "inspector.css").read_text(),
)

PAGES = {system["name"]: system["page"] for system in systems.SYSTEMS}

# The demo fault each machine can simulate from the inspector panel (keys of events.EVENTS).
SCENARIO_FOR = {
    "Chiller 1 · Dim Sum": "chiller_door_open",
    "Freezer 1 · Seafood": "freezer_fault",
    "Duck Oven": "oven_door_leak",
    "Dim Sum Forming": "forming_jam",
    "AI Quality Check": "defect_spike",
    "Dispatch": "banquet_order",
    amr.NAME: "amr_blocked",
    "Kitchen pass": "lunch_rush",
    foh_robot.NAME: "lunch_rush",
}

# A short description for zones that are not one of the seven systems.
NOTES = {
    "Receiving": "Goods-in dock for raw ingredients",
    "Dispatch": "Trays leave here for the restaurants",
}


def click_targets():
    """Which page the inspector's "Open page" button opens for each zone (or the robot)."""
    targets = {amr.NAME: PAGES["AMR Robot"]}
    for sensor in temperature.SENSORS:
        targets[sensor["name"]] = PAGES["IoT Temperature Monitoring"]
    for zone in layout.ZONES:
        if "system" in zone:
            targets[zone["name"]] = PAGES[zone["system"]]
    targets["Dispatch"] = PAGES["Demand Forecast"]
    return targets


def _scenario(name):
    """The inspector's fault button for a zone, or None if it has no demo fault."""
    key = SCENARIO_FOR.get(name)
    if key is None:
        return None
    return {"key": key, "label": events.EVENTS[key]["label"], "active": events.is_active(key)}


def _heat(sensor):
    """How close a reading is to its safe limit, for the twin's temperature layer.

    0 is well inside the safe range, 1 is at the limit, above 1 is beyond it.
    Hot holding has more room to move than the cold rooms, so its scale is wider.
    """
    margins = []
    if sensor["high"] is not None:
        margins.append(sensor["high"] - sensor["temp_c"])
    if sensor["low"] is not None:
        margins.append(sensor["temp_c"] - sensor["low"])
    scale = 10 if sensor["high"] is None else 4
    return round(max(0.0, 1 - min(margins) / scale), 2)


def _chart(title, unit, values, limits=(), targets=(), compare=None):
    """The last 10 minutes of one reading, for the mini-chart in the twin's inspector panel.

    Thinned to every fifth point (one every 10 s), always keeping the newest.
    limits / targets: (value, label) pairs drawn as dashed red / grey lines.
    compare: a second series drawn as a dashed grey line (e.g. the oven's recipe).
    """
    thin = lambda series: [round(float(v), 2) for v in list(series)[::-1][::5][::-1]]
    return {"title": title, "unit": unit, "values": thin(values), "compare": thin(compare) if compare is not None else None,
            "limits": [[float(v), label] for v, label in limits], "targets": [[float(v), label] for v, label in targets]}


def kitchen_charts(now):
    """Mini-charts for the kitchen zones, by zone name."""
    charts = {}
    readings = temperature.history(now)
    for sensor in temperature.SENSORS:
        limits = [(sensor[side], "Min" if side == "low" else "Max") for side in ("low", "high") if sensor[side] is not None]
        values = readings[readings["sensor"] == sensor["name"]]["temp_c"]
        charts[sensor["name"]] = _chart("Temperature", "°C", values, limits=limits)
    charts["Dim Sum Forming"] = _chart("Throughput", "pcs/min", forming.throughput(now)["ppm"],
                                       targets=[(forming.TARGET_PPM, "Target")])
    charts["AI Quality Check"] = _chart("Pass rate", "%", quality.inspections(now)["pass_rate"],
                                        limits=[(quality.TARGET_PASS_RATE, "Min")])
    oven = duck_oven.temperatures(now)
    charts["Duck Oven"] = _chart("Oven vs recipe", "°C", oven["actual"], compare=oven["recipe"])
    return charts


def kitchen_state(now):
    """What every zone and the robot look like right now."""
    sensors = {s["name"]: s for s in temperature.latest(now)}
    cards = {c["name"]: c for c in systems.summary(now)}
    targets = click_targets()
    charts = kitchen_charts(now)

    zones = []
    for zone in layout.ZONES:
        label, alert, door_open, subtitle, heat = "", False, False, NOTES.get(zone["name"], ""), None
        if zone["name"] in sensors:
            sensor = sensors[zone["name"]]
            label = f"{sensor['temp_c']:.1f} °C"
            alert = not sensor["ok"]
            door_open = sensor.get("event") == "chiller_door_open" and events.is_active("chiller_door_open")
            subtitle = f"Safe range {temperature.limit_text(sensor)}"
            heat = _heat(sensor)
        elif "system" in zone:
            card = cards[zone["system"]]
            label = card["value"]
            alert = bool(card["alerts"])
            subtitle = zone["system"]
        zones.append({**zone, "label": label, "alert": alert, "busy": False, "door_open": door_open,
                      "subtitle": subtitle, "heat": heat, "chart": charts.get(zone["name"]),
                      "scenario": _scenario(zone["name"]),
                      "has_page": zone["name"] in targets})

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
                "label": "", "carrying": True, "subtitle": "Autonomous tray carrier",
                "reading": robot["activity"], "scenario": _scenario(amr.NAME), "has_page": True},
    }


def dining_state(now):
    """The restaurant dining room: tables, the kitchen pass and the service robot."""
    # The simulator measures from the kitchen pass; the twin is centred on the room.
    def place(spot):
        return {"x": spot["x"] - 5.25, "z": spot["y"] - 3.5}

    orders = foh_robot.queue(now)
    waiting = {order["Table"] for order in orders}
    wait_chart = _chart("Average wait", "min", foh_robot.service(now)["wait_min"],
                        limits=[(foh_robot.MAX_WAIT_MIN, "Limit")])
    zones = [{
        "name": "Kitchen pass", "kind": "pass", **place(foh_robot.KITCHEN_PASS), "w": 1.6, "d": 4.0,
        "label": f"{len(orders)} order{'s' if len(orders) != 1 else ''} waiting", "alert": bool(foh_robot.status(now)["alerts"]),
        "busy": False, "door_open": False, "subtitle": "Dishes wait here for the robot",
        "scenario": _scenario("Kitchen pass"), "has_page": False, "chart": wait_chart,
    }]
    for table in foh_robot.TABLES:
        is_waiting = table["table"] in waiting
        zones.append({
            "name": f"T{table['table']}", "kind": "table", **place(table), "w": 2.3, "d": 2.3,
            "guests": table["guests"], "label": "Order waiting" if is_waiting else "",
            "alert": False, "busy": is_waiting, "served": not is_waiting, "door_open": False,
            "subtitle": f"{table['guests']} guests", "scenario": None, "has_page": False,
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
                "label": robot["short"], "carrying": robot["carrying"], "subtitle": "Three-tray serving robot",
                "reading": robot["activity"], "scenario": _scenario(foh_robot.NAME), "has_page": False,
                "chart": wait_chart},
    }


def _toggle_scenario(component_key):
    """Inspector button pressed: switch that scenario on or off, and keep the sidebar switch in step."""
    key = (st.session_state.get(component_key) or {}).get("scenario")
    if key not in events.EVENTS:
        return
    switch_on = not events.is_active(key)
    if switch_on:
        events.trigger(key)
    else:
        events.clear(key)
    st.session_state[f"event_{key}"] = switch_on
    st.session_state["scenario_changed"] = True


def _show(state, key, height, fill=None):
    """Draw a twin and act on its buttons. Returns the component result.

    fill: make the twin fill the window height, leaving this many pixels for a top bar.
    """
    state = {**state, "height": height, "fill": fill,
             "safety_zones_visible": st.session_state.get("safety_zones", False)}
    result = _draw(data=state, key=key, height="content" if fill else height, on_clicked_change=lambda: None,
                   on_scenario_change=lambda: _toggle_scenario(key))
    if st.session_state.pop("scenario_changed", False):
        st.rerun()  # a full rerun, so the sidebar and every panel show the new scenario state
    return result


def dining_twin(now, height=460, link_page=False, fill=None):
    """Draw the dining-room twin.

    link_page: give the kitchen pass and the robot an "Open page" button to the
    FOH Service Robot page (used on the Overview; not needed on that page itself).
    """
    state = dining_state(now)
    if link_page:
        for zone in state["zones"]:
            zone["has_page"] = zone["kind"] == "pass"
        state["amr"]["has_page"] = True
    result = _show({**state, "focus": "dining"}, "dining_twin", height, fill)
    if link_page and result.clicked:
        st.session_state["open_page"] = PAGES["FOH Service Robot"]
        st.rerun()


def kitchen_twin(now, focus="overview", height=460, fill=None):
    """Draw the kitchen twin. `focus` picks the starting camera:
    "overview", "cold_rooms", "amr", "forming" or "oven".

    Clicking a zone opens an inspector panel; its "Open page" button opens that system's page.
    """
    result = _show({**kitchen_state(now), "focus": focus}, "kitchen_twin", height, fill)
    page = click_targets().get(result.clicked)
    if page:
        # The twin sits inside an auto-refreshing fragment, so hand the request
        # to app.py, which switches page on a full rerun.
        st.session_state["open_page"] = page
        st.rerun()
