"""Imperial Treasure Smart Central Production Kitchen: class-demo entry point.

Run with:  streamlit run app.py
"""

import time

import streamlit as st

import ui
from sim import alert_log, events, systems
from sim.systems import SYSTEMS

st.set_page_config(page_title="Smart Central Kitchen", page_icon="🥟", layout="wide")
ui.load_css(presentation=st.session_state.get("presentation", False))

pages = [st.Page("views/overview.py", title="Overview", icon="🏠", default=True)]
pages += [st.Page(s["page"], title=s["name"], icon=s["icon"]) for s in SYSTEMS]
page = st.navigation(pages)

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

with st.sidebar:
    st.toggle("Safety Zone Overlay", key="safety_zones",
              help="Show colour-coded hazard and robot-traffic areas on the kitchen and dining-room twins.")
    st.markdown("🔴 **Zone A · Thermal & Mechanical** \nDuck Oven + Dim Sum Forming")
    st.markdown("🟠 **Zone B · Human & Robot traffic** \nMain Aisle + FOH Pass")
    st.markdown("🔵 **Zone C · Food Safety Environment** \nCold + Hot Holding")
    st.divider()

    st.header("Demo Controls")
    st.caption("Switch on an event, then watch the dashboards react. Switch it off to recover.")
    for system in SYSTEMS:
        system_events = {k: e for k, e in events.EVENTS.items() if e["system"] == system["name"]}
        if system_events:
            st.markdown(f"**{system['icon']} {system['name']}**")
        for key, event in system_events.items():
            st.toggle(event["label"], key=f"event_{key}", on_change=on_toggle, args=(key,))
    st.button("Reset all events", icon=":material/restart_alt:", on_click=reset_all, width="stretch")

    st.divider()
    st.toggle("Presentation mode", key="presentation",
              help="Larger text and no Streamlit toolbar, for projecting. Collapse this sidebar with « for a clean screen.")

page.run()
