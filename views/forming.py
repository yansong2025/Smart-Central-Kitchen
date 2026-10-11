import time

import altair as alt
import pandas as pd
import streamlit as st

import ui
from sim import forming
from twin import kitchen_twin

ui.page_header(
    "🥟",
    "Dim Sum Forming Machine",
    "Automatic line that wraps, fills and shapes dim sum, replacing hand-forming for high-volume items.",
)


def weight_chart(deviations):
    """How the latest pieces spread around their target weight, with the tolerance marked."""
    tolerance = forming.WEIGHT_TOLERANCE_G
    bars = alt.Chart(deviations).mark_bar(color=ui.SERIES_COLORS[0], cornerRadiusEnd=3).encode(
        x=alt.X("deviation_g:Q", bin=alt.Bin(step=0.2), title="Difference from target weight (g)",
                scale=alt.Scale(domain=[-1.4, 1.4])),
        y=alt.Y("count():Q", title="Pieces"),
        tooltip=[alt.Tooltip("count():Q", title="Pieces")],
    )
    limits = pd.DataFrame({"value": [-tolerance, tolerance], "label": [f"−{tolerance:.0f} g limit", f"+{tolerance:.0f} g limit"]})
    rules = alt.Chart(limits).mark_rule(color=ui.LIMIT_COLOR, strokeDash=[4, 4]).encode(x="value:Q")
    labels = alt.Chart(limits).mark_text(baseline="top", dy=2, fontSize=11).encode(x="value:Q", y=alt.value(0), text="label:N")
    return (bars + rules + labels).properties(height=220)


@st.fragment(run_every=ui.REFRESH_S)
def live_forming():
    now = time.time()
    history = forming.throughput(now)
    ppm = history["ppm"].iloc[-1]
    batch = forming.current_batch(now)
    product = batch["product"]

    ui.alert_banner(forming.status(now)["alerts"], "Forming line is running at target speed")
    ui.kpi_row([
        ("Throughput", f"{ppm:.0f} pcs/min"),
        ("Line speed vs target", f"{ppm / forming.TARGET_PPM:.0%}"),
        ("Pieces formed today", f"{forming.pieces_today(now):,}"),
        ("Downtime today", f"{forming.downtime_min(now):.1f} min"),
    ])

    left, right = st.columns([3, 2])
    with left, ui.card("Throughput, last 10 minutes"):
        ui.line_chart(history, "ppm", "pieces / min", key="throughput",
                      targets=[(forming.TARGET_PPM, f"Target {forming.TARGET_PPM}")])
    with right, ui.card(f"Piece weight, last 300 pieces (target {product['weight_g']} g)"):
        st.altair_chart(weight_chart(forming.weight_deviation(now)), key="weights")

    left, right = st.columns(2)
    with left, ui.card(f"Current batch: {product['name']} (batch #{batch['number']})"):
        st.progress(batch["progress"], text=f"{batch['progress']:.0%} complete")
    with right, ui.card("Filling hopper"):
        level = forming.hopper_level(now)
        st.progress(level / 100, text=f"{level:.0f}% full, topped up automatically at 25%")

    left, right = st.columns([3, 2])
    with left, ui.card("On the kitchen floor"):
        kitchen_twin(now, focus="forming", height=330)
    with right, ui.card("Before and after automation"):
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
