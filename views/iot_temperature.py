import time

import streamlit as st

import ui
from sim import temperature
from twin import kitchen_twin

ui.page_header(
    "🌡️",
    "IoT Temperature Monitoring",
    f"Wireless sensors in every cold room and hot-holding cabinet report every {temperature.STEP_S} seconds.",
)


@st.fragment(run_every=ui.REFRESH_S)
def live_sensors():
    now = time.time()
    readings = temperature.history(now)
    sensors = temperature.latest(now)

    ui.alert_banner(temperature.status(now)["alerts"], "All zones are within their safe temperature range")

    with ui.card("Cold rooms on the kitchen twin"):
        kitchen_twin(now, focus="cold_rooms", height=380)
        st.caption("Click a zone to open its page. Drag to rotate, scroll to zoom.")

    columns = st.columns(3)
    for i, sensor in enumerate(sensors):
        with columns[i % 3], ui.card(sensor["name"]):
            st.metric(f"Safe range {temperature.limit_text(sensor)}", f"{sensor['temp_c']:.1f} °C")
            ui.status_badge(sensor["ok"], "In range", "Out of range")
            limits = [(sensor[side], f"Limit {sensor[side]} °C") for side in ("low", "high") if sensor[side] is not None]
            ui.line_chart(
                readings[readings["sensor"] == sensor["name"]],
                "temp_c", "°C", key=f"temp_{i}", limits=limits, height=180,
            )


live_sensors()
