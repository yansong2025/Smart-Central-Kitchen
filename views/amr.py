import time

import streamlit as st

import ui
from sim import amr
from twin import kitchen_twin

ui.system_header(
    "AMR Robot",
    "Autonomous mobile robot that carries trays between receiving, cold rooms, production and dispatch.",
)


@st.fragment(run_every=ui.REFRESH_S)
def live_amr():
    now = time.time()
    robot = amr.state(now)
    battery = amr.battery(now)

    ui.alert_banner(amr.status(now)["alerts"], f"{amr.NAME} is running its delivery loop")
    ui.kpi_row([
        ui.kpi("Deliveries today", f"{amr.deliveries_today(now):,}", icon_name="local_shipping",
               note=f"Daily target {amr.DAILY_TARGET}"),
        ui.kpi("Loop time", f"{amr.LOOP_S:.0f}", unit="s", icon_name="route", note="One full delivery round"),
        ui.kpi("Time blocked today", f"{amr.blocked_seconds(now):.0f}", unit="s", icon_name="block",
               tone="crit" if robot["blocked"] else ""),
        ui.kpi("Battery", f"{battery:.0f}", unit="%", icon_name="battery_charging_80", bar=battery / 100,
               tone="warn" if battery < 45 else "ok"),
    ])

    left, right = st.columns([5, 3], gap="medium")
    with left, ui.card("Live position", "The dashed line is the delivery loop"):
        kitchen_twin(now, focus="amr", height=500)
        ui.twin_hint()
    with right:
        status = ui.status_pill(not robot["blocked"], "Moving", "Stopped")
        with ui.card(amr.NAME, "Autonomous tray carrier", aside=status):
            ui.facts([
                ("navigation", "Doing now", robot["activity"]),
                ("flag", "Next stop", robot["queue"][0]["Stop"] if robot["queue"] else "—"),
                ("battery_charging_80", "Battery", f"{battery:.0f}%"),
            ])
            st.html(ui.meter(battery / 100, "warn" if battery < 45 else "ok"))
        with ui.card("Next stops", "Arrival times on the current loop"):
            st.dataframe(robot["queue"], hide_index=True)


live_amr()
