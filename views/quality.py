import time

import altair as alt
import streamlit as st

import ui
from sim import quality

ui.page_header(
    "🔍",
    "AI Quality Check",
    "A camera over the line inspects every tray of dim sum and rejects trays with too many defects.",
)


def defect_chart(trays):
    """Defective pieces by type over the window, largest first."""
    counts = trays.groupby("defect_type", as_index=False)["defects"].sum()
    bars = alt.Chart(counts).mark_bar(color=ui.SERIES_COLORS[0], cornerRadiusEnd=4, height=22).encode(
        x=alt.X("defects:Q", title="Defective pieces"),
        y=alt.Y("defect_type:N", title=None, sort="-x"),
        tooltip=[alt.Tooltip("defect_type:N", title="Defect"), alt.Tooltip("defects:Q", title="Pieces")],
    )
    return bars.properties(height=220)


@st.fragment(run_every=ui.REFRESH_S)
def live_quality():
    now = time.time()
    trays = quality.inspections(now)

    ui.alert_banner(quality.status(now)["alerts"], "Quality is above target")
    ui.kpi_row([
        ("Pass rate, last 30 s", f"{trays['pass_rate'].iloc[-1]:.1f}%"),
        ("Pieces inspected today", f"{quality.pieces_inspected_today(now):,}"),
        ("Defects, last 10 min", f"{trays['defects'].sum():,}"),
        ("Trays rejected, last 10 min", f"{trays['rejected'].sum():,}"),
    ])

    left, right = st.columns([3, 2])
    with left, ui.card("Pass rate, last 10 minutes"):
        ui.line_chart(trays, "pass_rate", "% of pieces passed", key="pass_rate",
                      limits=[(quality.TARGET_PASS_RATE, f"Minimum {quality.TARGET_PASS_RATE:.0f}%")])
    with right, ui.card("Defects by type, last 10 minutes"):
        st.altair_chart(defect_chart(trays), key="defects")

    with ui.card("Latest trays inspected"):
        latest = trays.tail(8).iloc[::-1]
        st.dataframe(
            {
                "Time": latest["time"].dt.strftime("%H:%M:%S"),
                "Product": latest["product"],
                "Pieces": quality.TRAY_PIECES,
                "Defects": latest["defects"],
                "Main defect": latest["defect_type"].where(latest["defects"] > 0, "None"),
                "Result": latest["rejected"].map({True: "❌ Rejected", False: "✅ Passed"}),
                "AI confidence": latest["confidence"].map("{:.1%}".format),
            },
            hide_index=True,
        )


live_quality()
