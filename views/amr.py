import time

import streamlit as st

import ui
from sim import amr
from twin import kitchen_twin

ui.page_header(
    "🤖",
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
        ("Deliveries today", f"{amr.deliveries_today(now):,}"),
        ("Loop time", f"{amr.LOOP_S:.0f} s"),
        ("Time blocked today", f"{amr.blocked_seconds(now):.0f} s"),
        ("Battery", f"{battery:.0f}%"),
    ])

    left, right = st.columns([2, 1])
    with left, ui.card("Live position"):
        kitchen_twin(now, focus="amr")
        st.caption("The dashed line is the delivery loop. Click a zone to open its page. Drag to rotate, scroll to zoom.")
    with right:
        with ui.card(f"{amr.NAME} now"):
            st.markdown(robot["activity"])
            ui.status_badge(not robot["blocked"], "Moving normally", "Stopped")
            st.progress(battery / 100, text=f"Battery {battery:.0f}%")
        with ui.card("Next stops"):
            st.dataframe(robot["queue"], hide_index=True)


live_amr()
