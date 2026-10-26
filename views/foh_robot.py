import time

import streamlit as st

import ui
from sim import foh_robot
from twin import dining_twin

ui.system_header(
    "FOH Service Robot",
    "Front-of-house robot that carries dishes from the kitchen pass to the tables, so staff can stay with guests.",
)


@st.fragment(run_every=ui.REFRESH_S)
def live_foh():
    now = time.time()
    orders = foh_robot.queue(now)
    robot = foh_robot.position(now)
    battery = foh_robot.battery(now)
    service = foh_robot.service(now)
    wait = foh_robot.average_wait_min(now)
    alerts = foh_robot.status(now)["alerts"]

    ui.alert_banner(alerts, f"{foh_robot.NAME} is keeping up with orders")
    ui.kpi_row([
        ui.kpi("Orders waiting", len(orders), icon_name="receipt_long", note="At the kitchen pass or on the robot",
               tone="crit" if alerts else ""),
        ui.kpi("Average wait", f"{wait:.1f}", unit="min", icon_name="hourglass_top", spark=service["wait_min"].tail(120),
               note=f"Limit {foh_robot.MAX_WAIT_MIN:.0f} min", tone="crit" if alerts else ""),
        ui.kpi("Deliveries today", f"{foh_robot.deliveries_today(now):,}", icon_name="room_service",
               note=f"Daily target {foh_robot.DAILY_TARGET}"),
        ui.kpi("Guests seated", sum(t["guests"] for t in foh_robot.TABLES), icon_name="groups",
               note=f"Across {len(foh_robot.TABLES)} tables"),
    ])

    with ui.card("Dining room", "Tables with an orange floor are waiting for food"):
        dining_twin(now, height=520)
        ui.twin_hint()

    left, right = st.columns([2, 3], gap="medium")
    with left:
        status = ui.status_pill(not alerts, "Keeping up", "Falling behind")
        with ui.card(foh_robot.NAME, "Three-tray serving robot", aside=status):
            ui.facts([
                ("navigation", "Doing now", robot["activity"]),
                ("lunch_dining", "Carrying", "Dishes" if robot["carrying"] else "Nothing"),
                ("battery_charging_80", "Battery", f"{battery:.0f}%"),
            ])
            st.html(ui.meter(battery / 100, "warn" if battery < 45 else "ok"))
    with right, ui.card("Order queue", "Longest wait first · the top order is on the robot",
                        aside=ui.pill(f"{len(orders)} orders", "neutral")):
        st.dataframe(orders, hide_index=True, height=215)

    left, right = st.columns([3, 2], gap="medium")
    with left, ui.card("Average wait for food", "Minutes, last 10 minutes"):
        ui.line_chart(service, "wait_min", "minutes", key="wait",
                      limits=[(foh_robot.MAX_WAIT_MIN, f"Limit {foh_robot.MAX_WAIT_MIN:.0f} min")])
    with right, ui.card("Before and after the robot"):
        ui.comparison(
            [
                ("Kitchen trips per server, per hour", "20", "6"),
                ("Server time spent with guests", "55%", "80%"),
                ("Average wait for food", "3.5 min", "2.5 min"),
                ("Heavy trays carried by staff", "Every order", "Rush periods only"),
            ],
            before="Staff only", after="Staff + robot",
        )


live_foh()
