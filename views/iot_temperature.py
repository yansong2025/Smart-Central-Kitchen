import time

import streamlit as st

import ui
from sim import temperature
from twin import kitchen_twin

ui.system_header(
    "IoT Temperature Monitoring",
    f"Wireless sensors in every cold room and hot-holding cabinet report every {temperature.STEP_S} seconds.",
)


@st.fragment(run_every=ui.REFRESH_S)
def live_sensors():
    now = time.time()
    readings = temperature.history(now)
    sensors = temperature.latest(now)
    in_range = sum(s["ok"] for s in sensors)
    freezers = [s for s in sensors if s["name"].startswith("Freezer")]
    chillers = [s for s in sensors if s["name"].startswith("Chiller")]
    warmest_chiller = max(chillers, key=lambda s: s["temp_c"])
    warmest_freezer = max(freezers, key=lambda s: s["temp_c"])

    ui.alert_banner(temperature.status(now)["alerts"], "All zones are within their safe temperature range")
    ui.kpi_row([
        ui.kpi("Zones in range", in_range, unit=f"/ {len(sensors)}", icon_name="verified",
               bar=in_range / len(sensors), tone="ok" if in_range == len(sensors) else "crit"),
        ui.kpi("Warmest chiller", f"{warmest_chiller['temp_c']:.1f}", unit="°C", icon_name="kitchen",
               note=f"{warmest_chiller['name'].split(' · ')[0]} · limit {temperature.limit_text(warmest_chiller)}",
               tone="" if warmest_chiller["ok"] else "crit"),
        ui.kpi("Warmest freezer", f"{warmest_freezer['temp_c']:.1f}", unit="°C", icon_name="ac_unit",
               note=f"{warmest_freezer['name'].split(' · ')[0]} · limit {temperature.limit_text(warmest_freezer)}",
               tone="" if warmest_freezer["ok"] else "crit"),
        ui.kpi("Sensors online", len(sensors), unit=f"/ {len(sensors)}", icon_name="sensors",
               note=f"Reporting every {temperature.STEP_S} s"),
    ])

    with ui.card("Cold rooms on the kitchen twin", "Zones turn red when they leave their safe range"):
        kitchen_twin(now, focus="cold_rooms", height=380)
        ui.twin_hint()

    ui.section("Sensors", "Last 10 minutes")
    columns = st.columns(3, gap="medium")
    for i, sensor in enumerate(sensors):
        status = ui.status_pill(sensor["ok"], "In range", "Out of range")
        with columns[i % 3], ui.card(sensor["name"], aside=status):
            st.html(
                f'<div class="reading-value">{sensor["temp_c"]:.1f}<small>°C</small></div>'
                f'<div class="reading-range">Safe range {temperature.limit_text(sensor)}</div>'
            )
            limits = [(sensor[side], f"Limit {sensor[side]} °C") for side in ("low", "high") if sensor[side] is not None]
            ui.line_chart(
                readings[readings["sensor"] == sensor["name"]],
                "temp_c", "°C", key=f"temp_{i}", limits=limits, height=170,
            )


live_sensors()
