"""Shared UI components so every page looks and behaves the same.

Most components build a small piece of HTML styled by assets/style.css.
Icons are Material Symbols names (e.g. "conveyor_belt"), the same set Streamlit uses.
"""

import base64
import re
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from sim import alert_log
from sim.systems import SYSTEMS

REFRESH_S = 2  # how often live sections redraw

# Chart colours: blue and orange for data, red only for limits, grey for targets.
SERIES_COLORS = ["#2a78d6", "#eb6834"]
LIMIT_COLOR = "#d03b3b"
TARGET_COLOR = "#667085"
AXIS_COLOR = "#667085"
GRID_COLOR = "#eef0f3"


def load_css(presentation=False):
    """Apply the app's CSS. Presentation mode adds larger text and hides Streamlit's toolbar."""
    css = Path("assets/style.css").read_text()
    if presentation:
        css += Path("assets/presentation.css").read_text()
    st.html(f"<style>{css}</style>")


# ---- Small HTML building blocks ---------------------------------------------

def slug(text):
    """A string safe to use in a Streamlit key and CSS class name."""
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def icon(name):
    return f'<span class="mi">{name}</span>'


def pill(text, tone="neutral", icon_name=None):
    """A rounded status label. tone: ok, warn, crit, info or neutral."""
    return f'<span class="pill {tone}">{icon(icon_name) if icon_name else ""}{escape(str(text))}</span>'


def status_pill(ok, ok_text="Running", bad_text="Needs attention"):
    """Status as icon + text, so it never relies on colour alone."""
    if ok:
        return pill(ok_text, "ok", "check_circle")
    return pill(bad_text, "crit", "error")


def meter(fraction, tone="accent"):
    """A thin progress bar from 0 to 1."""
    width = max(0.0, min(float(fraction), 1.0)) * 100
    return f'<div class="meter {tone}"><span style="width:{width:.1f}%"></span></div>'


def sparkline(values, color=SERIES_COLORS[0]):
    """A tiny line chart for KPI tiles: an SVG drawn as an image (st.html strips inline SVG)."""
    values = [float(v) for v in values]
    low, high = min(values), max(values)
    span = (high - low) or 1.0
    width, height = 200, 34
    points = [
        (i * width / (len(values) - 1), height - 3 - (v - low) / span * (height - 6))
        for i, v in enumerate(values)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = f"0,{height} {line} {width},{height}"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
        f'<polygon points="{area}" fill="{color}" fill-opacity="0.10"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>'
    )
    data = base64.b64encode(svg.encode()).decode()
    return f'<img class="spark" alt="" src="data:image/svg+xml;base64,{data}">'


# ---- Page structure ------------------------------------------------------------

def page_header(icon_name, title, subtitle, crumb, live=True):
    """The page title block. live: show the pulsing "Live" badge (pages that refresh themselves)."""
    badge = (f'<div class="live"><i></i>Live · updates every {REFRESH_S} s</div>' if live
             else f'<div class="live">{icon("calendar_month")}Updated daily</div>')
    st.html(
        f'<div class="ph"><div class="ph-left"><div class="ph-icon">{icon(icon_name)}</div>'
        f'<div><div class="ph-crumb">{escape(crumb)}</div><h1>{escape(title)}</h1>'
        f'<p>{escape(subtitle)}</p></div></div>{badge}</div>'
    )


def system_header(system_name, subtitle, live=True):
    """Page header for one of the seven systems, using its icon and section from sim/systems.py."""
    system = next(s for s in SYSTEMS if s["name"] == system_name)
    page_header(system["icon"], system_name, subtitle, crumb=system["section"], live=live)


def section(title, note=""):
    st.html(f'<div class="sec"><h3>{escape(title)}</h3><span>{escape(note)}</span></div>')


def card(title, subtitle="", aside="", key=None):
    """A white card with a title. Use as `with ui.card("Title"):`.

    aside: HTML shown on the right of the title (a pill, for example).
    key: needed when the title changes while the page runs, or is not unique on the page.
    """
    box = st.container(key=f"card-{slug(key or title)}")
    sub = f'<div class="card-sub">{escape(subtitle)}</div>' if subtitle else ""
    box.html(f'<div class="card-head"><div><div class="card-title">{escape(title)}</div>{sub}</div>{aside}</div>')
    return box


def kpi(label, value, unit="", icon_name="", note="", spark=None, bar=None, tone=""):
    """One KPI tile for `kpi_row`. spark: recent values; bar: a 0 to 1 progress fraction."""
    return dict(label=label, value=value, unit=unit, icon_name=icon_name, note=note, spark=spark, bar=bar, tone=tone)


def kpi_row(tiles):
    """A responsive row of KPI tiles built with `kpi(...)`."""
    parts = []
    for t in tiles:
        unit = f'<span class="kpi-unit">{escape(str(t["unit"]))}</span>' if t["unit"] else ""
        note = f'<div class="kpi-note">{escape(t["note"])}</div>' if t["note"] else ""
        foot = ""
        if t["spark"] is not None:
            foot = f'<div class="kpi-foot">{sparkline(t["spark"])}</div>'
        elif t["bar"] is not None:
            foot = f'<div class="kpi-foot">{meter(t["bar"], t["tone"] or "accent")}</div>'
        parts.append(
            f'<div class="kpi {t["tone"]}"><div class="kpi-top"><span>{escape(t["label"])}</span>'
            f'{icon(t["icon_name"]) if t["icon_name"] else ""}</div>'
            f'<div class="kpi-value">{escape(str(t["value"]))}{unit}</div>{note}{foot}</div>'
        )
    st.html(f'<div class="kpis" style="--n:{len(parts)}">{"".join(parts)}</div>')


def facts(rows):
    """Label / value rows. Each row is (icon name, label, value HTML)."""
    html = "".join(
        f'<div class="fact"><span class="fact-label">{icon(i) if i else ""}{escape(label)}</span>'
        f'<span class="fact-value">{value}</span></div>'
        for i, label, value in rows
    )
    st.html(f'<div class="facts">{html}</div>')


def twin_hint(clickable=True):
    """How to use the 3D view, shown under each twin."""
    items = [("ads_click", "Click a machine to inspect it or simulate a fault")] if clickable else []
    items += [("3d_rotation", "Drag to rotate"), ("zoom_in", "Scroll to zoom")]
    st.html('<div class="hint">' + "".join(f"<span>{icon(i)}{t}</span>" for i, t in items) + "</div>")


def comparison(rows, before, after):
    """A before-and-after table from (measure, before value, after value) rows."""
    body = "".join(
        f'<tr><td>{escape(m)}</td><td>{escape(b)}</td><td class="after">{escape(a)}</td></tr>' for m, b, a in rows
    )
    st.html(
        f'<table class="cmp"><tr><th>Measure</th><th>{escape(before)}</th><th class="after">{escape(after)}</th></tr>'
        f'{body}</table><div class="foot">Illustrative figures for the class demo, not measured data.</div>'
    )


# ---- Alerts -------------------------------------------------------------------------

def alert_banner(alerts, ok_text, title=None, compact=False):
    """An alert card per alert (see `events.alert`), or one green "all clear" bar when there are none.

    Each card says what is wrong, what it costs and what to do. `title` names the system.
    compact: leave out the impact line, for the Overview where cards sit side by side.
    An alert is red with an Acknowledge button until an operator acknowledges it,
    then amber until the problem is resolved.

    Everything sits in one container, so the page below keeps its place in Streamlit's
    layout when alerts come and go. Otherwise a 3D twin further down would be rebuilt
    (closing its inspector panel) every time an alert appears.
    """
    with st.container():
        if not alerts:
            if ok_text:
                st.html(f'<div class="allclear">{icon("check_circle")}<span>{escape(ok_text)}</span></div>')
            return
        for alert in alerts:
            acknowledged = alert_log.acknowledged_at(alert["key"])
            state = "ack" if acknowledged else ("info" if alert["severity"] == "notice" else "crit")
            with st.container(key=f"alert-{state}-{slug(alert['key'])}"):
                st.html(_alert_html(alert, acknowledged, title, compact))
                if not acknowledged and alert_log.is_logged(alert["key"]):
                    st.button("Acknowledge", key=f"acknowledge-{slug(alert['key'])}", icon=":material/check:",
                              on_click=alert_log.acknowledge, args=(alert["key"],))


def _alert_html(alert, acknowledged, title, compact=False):
    raised = alert_log.raised_at(alert["key"])
    if acknowledged:
        badge = pill("Acknowledged", "warn", "engineering")
    elif alert["severity"] == "notice":
        badge = pill("Notice", "info", "info")
    else:
        badge = pill("Critical", "crit", "error")
    system = f'<div class="al-sys">{escape(title)}</div>' if title else ""
    when = f"Raised {alert_log.clock_time(raised)}" if raised else "Just now"
    handled = ""
    if acknowledged:
        handled = (f'<div class="al-row">{icon("schedule")}<div><b>Status</b>Acknowledged at '
                   f'{alert_log.clock_time(acknowledged)}, being handled</div></div>')
    impact = "" if compact else (
        f'<div class="al-row">{icon("payments")}<div><b>Impact</b>{escape(alert["impact"])} <em>(simulated)</em></div></div>'
    )
    return (
        f'<div class="al-top">{badge}<span class="al-time">{when}</span></div>'
        f'{system}<div class="al-title">{escape(alert["message"])}</div>'
        f'<div class="al-rows">{impact}'
        f'<div class="al-row">{icon("build")}<div><b>Action</b>{escape(alert["action"])}</div></div>'
        f"{handled}</div>"
    )


# ---- Charts ---------------------------------------------------------------------------

def show_chart(chart, key, height=220):
    """Draw an Altair chart in the app's chart style."""
    styled = (
        chart.properties(height=height)
        .configure(font="Inter, sans-serif", background="transparent")
        .configure_view(stroke=None)
        .configure_axis(
            labelColor=AXIS_COLOR, titleColor=AXIS_COLOR, labelFontSize=11, titleFontSize=11,
            titleFontWeight=500, gridColor=GRID_COLOR, domainColor="#e4e7ec", tickColor="#e4e7ec",
            labelPadding=6, titlePadding=10,
        )
        .configure_axisX(grid=False)
        .configure_legend(labelColor="#475467", labelFontSize=12, symbolType="circle", symbolSize=70, title=None)
    )
    st.altair_chart(styled, key=key, theme=None)


def _reference_lines(lines, color):
    """Dashed horizontal lines with a text label, from (value, label) pairs."""
    data = pd.DataFrame(lines, columns=["value", "label"])
    rules = alt.Chart(data).mark_rule(color=color, strokeDash=[4, 4], strokeWidth=1.2).encode(y="value:Q")
    labels = (
        alt.Chart(data)
        .mark_text(align="left", baseline="bottom", dx=4, dy=-3, fontSize=11, fontWeight=500, color=color)
        .encode(x=alt.value(0), y="value:Q", text="label:N")
    )
    return [rules, labels]


def line_chart(data, y, y_title, key, limits=(), targets=(), height=220):
    """Line chart over the "time" column.

    y: a column name, or {column: legend label} to draw several lines.
    limits / targets: (value, label) pairs drawn as dashed red / grey lines.
    """
    x = alt.X("time:T", title=None, axis=alt.Axis(format="%H:%M", tickCount=5))
    layers = []
    if isinstance(y, dict):
        data = data.melt(id_vars="time", value_vars=list(y), var_name="series", value_name="value")
        data["series"] = data["series"].map(y)
        names = list(y.values())
        color = alt.Color("series:N", legend=alt.Legend(orient="top", direction="horizontal"),
                          scale=alt.Scale(domain=names, range=SERIES_COLORS[:len(names)]))
        tooltip = [alt.Tooltip("series:N", title="Series")]
    else:
        data = data.rename(columns={y: "value"})
        color = alt.value(SERIES_COLORS[0])
        tooltip = []
        # A soft fill under a single line. It stops at the lowest value so the axis keeps fitting the data.
        fill = alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0, stops=[
            alt.GradientStop(color="rgba(42,120,214,0)", offset=0),
            alt.GradientStop(color="rgba(42,120,214,0.16)", offset=1),
        ])
        layers.append(alt.Chart(data).mark_area(color=fill).encode(
            x=x, y=alt.Y("value:Q", scale=alt.Scale(zero=False)), y2=alt.datum(float(data["value"].min()))))

    y_axis = alt.Y("value:Q", title=y_title, scale=alt.Scale(zero=False))
    layers.append(alt.Chart(data).mark_line(strokeWidth=2).encode(x=x, y=y_axis, color=color))
    # Invisible points give the tooltip a bigger target than the thin line.
    layers.append(alt.Chart(data).mark_point(size=140, opacity=0).encode(
        x=x, y=y_axis, color=color,
        tooltip=[alt.Tooltip("time:T", title="Time", format="%H:%M:%S"), *tooltip,
                 alt.Tooltip("value:Q", title=y_title, format=".1f")],
    ))
    if limits:
        layers += _reference_lines(limits, LIMIT_COLOR)
    if targets:
        layers += _reference_lines(targets, TARGET_COLOR)
    show_chart(alt.layer(*layers), key=key, height=height)
