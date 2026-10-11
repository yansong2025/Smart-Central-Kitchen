"""Shared UI helpers so every page looks and behaves the same."""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from sim import alert_log

REFRESH_S = 2  # how often live sections redraw

# Chart colours: blue and orange for data, red only for limits, grey for targets.
SERIES_COLORS = ["#2a78d6", "#eb6834"]
LIMIT_COLOR = "#d03b3b"
TARGET_COLOR = "#6b675f"


def load_css(presentation=False):
    """Apply the app's CSS. Presentation mode adds larger text and hides Streamlit's toolbar."""
    css = Path("assets/style.css").read_text()
    if presentation:
        css += Path("assets/presentation.css").read_text()
    st.html(f"<style>{css}</style>")


def page_header(icon, title, subtitle):
    st.html(f'<div class="page-header"><h1>{icon} {title}</h1><p>{subtitle}</p></div>')


def alert_banner(alerts, ok_text, title=None):
    """A banner per alert (see `events.alert`), or one green banner when there are none.

    Each banner says what is wrong, what it costs and what to do. `title` adds a heading line.
    An alert is red with an Acknowledge button until an operator acknowledges it,
    then amber until the problem is resolved.
    """
    if not alerts:
        st.success(ok_text, icon="✅")
    for alert in alerts:
        heading = f"**{title}**  \n" if title else ""
        text = (
            f"{heading}**{alert['message']}**  \n"
            f"Impact: {alert['impact']} (simulated)  \n"
            f"Action: {alert['action']}"
        )
        acknowledged = alert_log.acknowledged_at(alert["key"])
        if acknowledged:
            st.warning(f"{text}  \nAcknowledged at {alert_log.clock_time(acknowledged)}: being handled", icon="🛠️")
        else:
            st.error(text, icon="🚨")
            if alert_log.is_logged(alert["key"]):
                st.button("Acknowledge", key=f"acknowledge {alert['key']}", icon=":material/check:",
                          on_click=alert_log.acknowledge, args=(alert["key"],))


def comparison(rows, before, after):
    """A small before-and-after table from (measure, before value, after value) rows."""
    st.table(pd.DataFrame(rows, columns=["Measure", before, after]).set_index("Measure"))
    st.caption("Illustrative figures for the class demo, not measured data.")


def status_badge(ok, ok_text="Running", bad_text="Needs attention"):
    """Status as icon + text, so it never relies on colour alone."""
    if ok:
        st.badge(ok_text, icon=":material/check_circle:", color="green")
    else:
        st.badge(bad_text, icon=":material/warning:", color="red")


def kpi_row(items):
    """A row of metric cards from (label, value) pairs."""
    for column, (label, value) in zip(st.columns(len(items)), items):
        column.metric(label, value, border=True)


def card(title):
    """A white bordered box with a bold title. Use as `with ui.card("Title"):`."""
    box = st.container(border=True)
    box.markdown(f"**{title}**")
    return box


def _reference_lines(lines, color):
    """Dashed horizontal lines with a text label, from (value, label) pairs."""
    data = pd.DataFrame(lines, columns=["value", "label"])
    rules = alt.Chart(data).mark_rule(color=color, strokeDash=[4, 4]).encode(y="value:Q")
    labels = (
        alt.Chart(data)
        .mark_text(align="left", baseline="bottom", dx=4, dy=-2, fontSize=11)
        .encode(x=alt.value(0), y="value:Q", text="label:N")
    )
    return [rules, labels]


def line_chart(data, y, y_title, key, limits=(), targets=(), height=220):
    """Line chart over the "time" column.

    y: a column name, or {column: legend label} to draw several lines.
    limits / targets: (value, label) pairs drawn as dashed red / grey lines.
    """
    if isinstance(y, dict):
        data = data.melt(id_vars="time", value_vars=list(y), var_name="series", value_name="value")
        data["series"] = data["series"].map(y)
        names = list(y.values())
        color = alt.Color(
            "series:N", title=None, legend=alt.Legend(orient="top"),
            scale=alt.Scale(domain=names, range=SERIES_COLORS[:len(names)]),
        )
        tooltip = [alt.Tooltip("series:N", title="Series")]
    else:
        data = data.rename(columns={y: "value"})
        color = alt.value(SERIES_COLORS[0])
        tooltip = []

    line = alt.Chart(data).mark_line(strokeWidth=2).encode(
        x=alt.X("time:T", title=None, axis=alt.Axis(format="%H:%M", tickCount=5)),
        y=alt.Y("value:Q", title=y_title, scale=alt.Scale(zero=False)),
        color=color,
        tooltip=[
            alt.Tooltip("time:T", title="Time", format="%H:%M:%S"),
            *tooltip,
            alt.Tooltip("value:Q", title=y_title, format=".1f"),
        ],
    )
    layers = [line]
    if limits:
        layers += _reference_lines(limits, LIMIT_COLOR)
    if targets:
        layers += _reference_lines(targets, TARGET_COLOR)
    st.altair_chart(alt.layer(*layers).properties(height=height), key=key)
