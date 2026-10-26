import time

import altair as alt
import pandas as pd
import streamlit as st

import ui
from sim import forming
from twin import kitchen_twin

ui.system_header(
    "Dim Sum Forming Machine",
    "Automatic line that wraps, fills and shapes dim sum, replacing hand-forming for high-volume items.",
)


def weight_chart(deviations):
    """How the latest pieces spread around their target weight, with the tolerance marked."""
    tolerance = forming.WEIGHT_TOLERANCE_G
    bars = alt.Chart(deviations).mark_bar(color=ui.SERIES_COLORS[0], cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("deviation_g:Q", bin=alt.Bin(step=0.2), title="Difference from target weight (g)",
                scale=alt.Scale(domain=[-1.4, 1.4])),
        y=alt.Y("count():Q", title="Pieces"),
        tooltip=[alt.Tooltip("count():Q", title="Pieces")],
    )
    limits = pd.DataFrame({"value": [-tolerance, tolerance],
                           "label": [f"−{tolerance:.0f} g", f"+{tolerance:.0f} g"]})
    rules = alt.Chart(limits).mark_rule(color=ui.LIMIT_COLOR, strokeDash=[4, 4]).encode(x="value:Q")
    labels = alt.Chart(limits).mark_text(baseline="top", dy=2, dx=4, align="left", fontSize=11,
                                         color=ui.LIMIT_COLOR).encode(x="value:Q", y=alt.value(0), text="label:N")
    return bars + rules + labels


@st.fragment(run_every=ui.REFRESH_S)
def live_forming():
    now = time.time()
    history = forming.throughput(now)
    ppm = history["ppm"].iloc[-1]
    batch = forming.current_batch(now)
    product = batch["product"]
    hopper = forming.hopper_level(now)

    ui.alert_banner(forming.status(now)["alerts"], "Forming line is running at target speed")
    ui.kpi_row([
        ui.kpi("Throughput", f"{ppm:.0f}", unit="pcs/min", icon_name="speed", spark=history["ppm"].tail(120),
               tone="crit" if ppm < forming.TARGET_PPM / 2 else ""),
        ui.kpi("Line speed vs target", f"{ppm / forming.TARGET_PPM:.0%}", icon_name="track_changes",
               note=f"Target {forming.TARGET_PPM} pcs/min", bar=ppm / forming.TARGET_PPM,
               tone="crit" if ppm < forming.TARGET_PPM / 2 else "ok"),
        ui.kpi("Pieces formed today", f"{forming.pieces_today(now):,}", icon_name="inventory_2",
               note=f"Daily target {forming.DAILY_TARGET:,}"),
        ui.kpi("Downtime today", f"{forming.downtime_min(now):.1f}", unit="min", icon_name="timer",
               note="Includes planned changeovers"),
    ])

    left, right = st.columns([3, 2], gap="medium")
    with left, ui.card("Throughput", "Pieces per minute, last 10 minutes"):
        ui.line_chart(history, "ppm", "pieces / min", key="throughput",
                      targets=[(forming.TARGET_PPM, f"Target {forming.TARGET_PPM}")])
    with right, ui.card("Piece weight", f"Last 300 pieces against the {product['weight_g']} g target"):
        ui.show_chart(weight_chart(forming.weight_deviation(now)), key="weights")

    left, right = st.columns([3, 2], gap="medium")
    with left, ui.card("On the kitchen floor", "Close-up of the forming line on the digital twin"):
        kitchen_twin(now, focus="forming", height=360)
        ui.twin_hint()
    with right:
        with ui.card("Current batch", aside=ui.pill(f"Batch #{batch['number']}", "neutral")):
            ui.facts([
                ("restaurant", "Product", product["name"]),
                ("scale", "Target weight", f"{product['weight_g']} g ± {forming.WEIGHT_TOLERANCE_G:.0f} g"),
                ("pending_actions", "Batch progress", f"{batch['progress']:.0%}"),
                ("water_full", "Filling hopper", f"{hopper:.0f}% full"),
            ])
            st.html(ui.meter(hopper / 100, "warn" if hopper < 35 else "info")
                    + '<div class="card-sub">The hopper is topped up automatically at 25%.</div>')
        with ui.card("Before and after automation"):
            ui.comparison(
                [
                    ("Output per hour", "2,400 pieces", f"{forming.TARGET_PPM * 60:,} pieces"),
                    ("Staff on the line", "8", "2"),
                    ("Weight variation", "± 3 g", f"± {forming.WEIGHT_TOLERANCE_G:.0f} g"),
                    ("Product changeover", "Retrain and re-brief staff", "Swap the mould, about 4 min"),
                ],
                before="Hand-forming", after="Forming machine",
            )


live_forming()
