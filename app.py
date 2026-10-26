"""Imperial Treasure Smart Central Production Kitchen: class-demo entry point.

Run with:  streamlit run app.py
"""

import time
from html import escape

import streamlit as st

import ui
from sim import alert_log, events, systems
from sim.systems import SYSTEMS

st.set_page_config(page_title="Smart Central Kitchen", page_icon="assets/logo-mark.svg", layout="wide")
ui.load_css(presentation=st.session_state.get("presentation", False))
st.logo("assets/logo.svg", size="large", icon_image="assets/logo-mark.svg")

# Navigation: the Overview, then the systems grouped by their section.
sections = {"": [
    st.Page("views/overview.py", title="Overview", icon=":material/space_dashboard:", default=True),
    st.Page("views/present.py", title="Full-screen twin", icon=":material/fullscreen:"),
]}
for system in SYSTEMS:
    page = st.Page(system["page"], title=system["name"], icon=f":material/{system['icon']}:")
    sections.setdefault(system["section"], []).append(page)
page = st.navigation(sections)

# A click on the 3D twin asks for a page (see twin/__init__.py).
if "open_page" in st.session_state:
    st.switch_page(st.session_state.pop("open_page"))


def on_toggle(key):
    if st.session_state[f"event_{key}"]:
        events.trigger(key)
    else:
        events.clear(key)


def reset_all():
    events.clear_all()
    for key in events.EVENTS:
        st.session_state[f"event_{key}"] = False


@st.fragment(run_every=ui.REFRESH_S)
def track_alerts():
    """Keeps the alert log up to date on every page. Draws nothing."""
    now = time.time()
    alert_log.update(systems.summary(now), now)


track_alerts()


def sidebar_heading(title, aside=""):
    st.html(f'<div class="side-h"><b>{escape(title)}</b>{aside}</div>')


def switch_row(kind, on, icon_name, title, subtitle, widget_key, **toggle_args):
    """A sidebar row: icon, title and subtitle on the left, the switch on the right.

    kind: "scenario" (red when on) or "setting" (grey when on); assets/style.css styles each.
    """
    state = "on" if on else "off"
    with st.container(key=f"{kind}-{state}-{widget_key}", horizontal=True, vertical_alignment="center", gap="small"):
        st.html(
            f'<div class="scn">{ui.icon(icon_name)}<div><div class="scn-title">{escape(title)}</div>'
            f'<div class="scn-system">{escape(subtitle)}</div></div></div>'
        )
        st.toggle(title, key=widget_key, label_visibility="collapsed", **toggle_args)


with st.sidebar:
    active = sum(events.is_active(key) for key in events.EVENTS)
    sidebar_heading("Scenario simulator", ui.pill(f"{active} active", "crit") if active else "")
    st.html('<div class="side-p">Switch on a fault to see every dashboard react.</div>')
    systems_by_name = {s["name"]: s for s in SYSTEMS}
    with st.container(key="scenarios"):
        for key, event in events.EVENTS.items():
            system = systems_by_name[event["system"]]
            switch_row("scenario", events.is_active(key), system["icon"], event["label"], system["name"],
                       f"event_{key}", on_change=on_toggle, args=(key,))
    if active:
        st.button("Reset all scenarios", icon=":material/restart_alt:", on_click=reset_all, width="stretch")

    st.divider()
    sidebar_heading("Display")
    switch_row("setting", st.session_state.get("safety_zones", False), "layers", "Safety zone overlay",
               "Hazard and robot-traffic areas on the twins", "safety_zones")
    if st.session_state.get("safety_zones"):
        st.html(
            '<div class="legend">'
            '<div><i style="background:#d03b3b"></i>Zone A · Thermal &amp; mechanical<small>Duck oven, dim sum forming</small></div>'
            '<div><i style="background:#e6a12c"></i>Zone B · People &amp; robot traffic<small>Main aisle, FOH pass</small></div>'
            '<div><i style="background:#2a78d6"></i>Zone C · Food safety environment<small>Cold rooms, hot holding</small></div>'
            "</div>"
        )
    switch_row("setting", st.session_state.get("presentation", False), "slideshow", "Presentation mode",
               "Larger text, no toolbar, for projecting", "presentation")

page.run()
