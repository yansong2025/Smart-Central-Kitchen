import time

import streamlit as st

import ui
from sim import foh_robot
from twin import dining_twin

ui.page_header(
    "🍽️",
    "FOH Service Robot",
    "Front-of-house robot that carries dishes from the kitchen pass to the tables, so staff can stay with guests.",
)


@st.fragment(run_every=ui.REFRESH_S)
def live_foh():
    now = time.time()
    orders = foh_robot.queue(now)
    robot = foh_robot.position(now)
    battery = foh_robot.battery(now)
    alerts = foh_robot.status(now)["alerts"]

    ui.alert_banner(alerts, f"{foh_robot.NAME} is keeping up with orders")
    ui.kpi_row([
        ("Orders waiting", len(orders)),
        ("Average wait", f"{foh_robot.average_wait_min(now):.1f} min"),
        ("Deliveries today", f"{foh_robot.deliveries_today(now):,}"),
        ("Guests in the dining room", sum(table["guests"] for table in foh_robot.TABLES)),
    ])

    left, right = st.columns([2, 1])
    with left, ui.card("Dining room"):
        dining_twin(now)
        st.caption("Tables with an orange floor are waiting for food. Drag to rotate, scroll to zoom.")
    with right:
        with ui.card(f"{foh_robot.NAME} now"):
            st.markdown(robot["activity"])
            ui.status_badge(not alerts, "Keeping up", "Falling behind")
            st.progress(battery / 100, text=f"Battery {battery:.0f}%")
        with ui.card("Order queue"):
            st.dataframe(orders, hide_index=True, height=248)

    left, right = st.columns([3, 2])
    with left, ui.card("Average wait for food, last 10 minutes"):
        ui.line_chart(foh_robot.service(now), "wait_min", "minutes", key="wait",
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
