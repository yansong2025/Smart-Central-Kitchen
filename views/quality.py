import time

import altair as alt
import streamlit as st

import ui
from sim import quality

ui.system_header(
    "AI Quality Check",
    "A camera over the line inspects every tray of dim sum and rejects trays with too many defects.",
)


def defect_chart(trays):
    """Defective pieces by type over the window, largest first."""
    counts = trays.groupby("defect_type", as_index=False)["defects"].sum()
    return alt.Chart(counts).mark_bar(color=ui.SERIES_COLORS[0], cornerRadiusEnd=4, height=20).encode(
        x=alt.X("defects:Q", title="Defective pieces", axis=alt.Axis(tickCount=4)),
        y=alt.Y("defect_type:N", title=None, sort="-x"),
        tooltip=[alt.Tooltip("defect_type:N", title="Defect"), alt.Tooltip("defects:Q", title="Pieces")],
    )


@st.fragment(run_every=ui.REFRESH_S)
def live_quality():
    now = time.time()
    trays = quality.inspections(now)
    rate = trays["pass_rate"].iloc[-1]
    below = rate < quality.TARGET_PASS_RATE

    ui.alert_banner(quality.status(now)["alerts"], "Quality is above target")
    ui.kpi_row([
        ui.kpi("Pass rate", f"{rate:.1f}", unit="%", icon_name="verified", spark=trays["pass_rate"].tail(120),
               note=f"Last 30 s · minimum {quality.TARGET_PASS_RATE:.0f}%", tone="crit" if below else ""),
        ui.kpi("Pieces inspected today", f"{quality.pieces_inspected_today(now):,}", icon_name="document_scanner",
               note=f"{quality.TRAY_PIECES} pieces per tray"),
        ui.kpi("Defects", f"{trays['defects'].sum():,}", icon_name="report", note="Last 10 minutes"),
        ui.kpi("Trays rejected", f"{trays['rejected'].sum():,}", icon_name="block",
               note=f"Last 10 minutes · {quality.REJECT_TRAY_AT}+ defects rejects a tray"),
    ])

    left, right = st.columns([3, 2], gap="medium")
    with left, ui.card("Pass rate", "Share of pieces passed, last 10 minutes"):
        ui.line_chart(trays, "pass_rate", "% passed", key="pass_rate",
                      limits=[(quality.TARGET_PASS_RATE, f"Minimum {quality.TARGET_PASS_RATE:.0f}%")])
    with right, ui.card("Defects by type", "Last 10 minutes"):
        ui.show_chart(defect_chart(trays), key="defects")

    latest = trays.tail(8).iloc[::-1]
    with ui.card("Latest trays inspected", "Newest first"):
        st.dataframe(
            {
                "Time": latest["time"].dt.strftime("%H:%M:%S"),
                "Product": latest["product"],
                "Defects": latest["defects"],
                "Main defect": latest["defect_type"].where(latest["defects"] > 0, "None"),
                "Result": latest["rejected"].map({True: "Rejected", False: "Passed"}),
                "AI confidence": latest["confidence"] * 100,
            },
            hide_index=True,
            column_config={
                "Defects": st.column_config.NumberColumn(help=f"Out of {quality.TRAY_PIECES} pieces"),
                "AI confidence": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )


live_quality()
