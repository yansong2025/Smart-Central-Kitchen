"""Full-screen digital twin, for presenting: only the 3D view and a slim top bar."""

import time

import streamlit as st

import ui
from sim import systems
from twin import dining_twin, kitchen_twin

TOP_BAR_PX = 74  # space the twin leaves for the bar above it

# Hide everything except this page's content: sidebar, header and page padding.
st.html("""<style>
  [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stHeader"],
  [data-testid="stExpandSidebarButton"] { display: none !important; }
  .block-container { padding: 12px 16px 0 !important; max-width: 100% !important; }
  .st-key-present-bar { gap: 14px; }
  .present-title { display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 680; color: #101828; }
  .present-mark { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center;
    background: #b42318; color: #ffffff; }
  .present-mark .mi { font-size: 19px; }
</style>""")

if "present_space" not in st.session_state:
    st.session_state["present_space"] = "Kitchen"


def exit_present():
    st.session_state["open_page"] = "views/overview.py"


@st.fragment(run_every=ui.REFRESH_S)
def live_present():
    now = time.time()
    open_alerts = sum(len(card["alerts"]) for card in systems.summary(now))

    with st.container(key="present-bar", horizontal=True, vertical_alignment="center"):
        st.html(f'<div class="present-title"><span class="present-mark">{ui.icon("view_in_ar")}</span>'
                "Smart CPK · Digital twin</div>")
        st.segmented_control(
            "View", ["Kitchen", "Dining room"], key="present_space", label_visibility="collapsed",
            format_func=lambda name: {"Kitchen": ":material/kitchen: Central kitchen",
                                      "Dining room": ":material/room_service: Front of house"}[name],
        )
        st.html(ui.pill(f"{open_alerts} open alert{'s' if open_alerts != 1 else ''}", "crit") if open_alerts
                else ui.pill("All systems normal", "ok"))
        st.space("stretch")
        if st.button("Exit", icon=":material/close_fullscreen:", on_click=exit_present):
            st.rerun()

    if st.session_state.get("present_space") == "Dining room":
        dining_twin(now, link_page=True, fill=TOP_BAR_PX)
    else:
        kitchen_twin(now, focus="overview", fill=TOP_BAR_PX)


live_present()
