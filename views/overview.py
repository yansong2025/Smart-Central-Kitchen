import time

import streamlit as st

import ui
from sim import alert_log, clock, duck_oven, forming, systems
from twin import kitchen_twin

ui.page_header(
    "🏠",
    "Imperial Treasure Smart Central Production Kitchen",
    "Live view of the seven smart systems. Class demo: all data is simulated.",
)


@st.fragment(run_every=ui.REFRESH_S)
def live_overview():
    now = time.time()
    cards = systems.summary(now)
    alerting = [card for card in cards if card["alerts"]]

    ui.kpi_row([
        ("Systems online", f"{len(cards)} / {len(cards)}"),
        ("Needing attention", len(alerting)),
        ("Dim sum formed today", f"{forming.pieces_today(now):,}"),
        ("Ducks roasted today", f"{duck_oven.ducks_today(now):,}"),
        ("Shift progress", f"{clock.shift_progress(now):.0%}"),
    ])

    twin_column, alert_column = st.columns([2, 1])
    with twin_column, ui.card("Kitchen digital twin"):
        kitchen_twin(now, focus="overview")
        st.caption("Click a zone to open its page. Drag to rotate, scroll to zoom, right-drag to pan.")
    with alert_column, ui.card("Live alerts"):
        with st.container(height=478, border=False):
            if not alerting:
                st.success("All systems normal", icon="✅")
            for card in alerting:
                ui.alert_banner(card["alerts"], "", title=card["name"])

    st.subheader("Systems")
    for row_start in range(0, len(cards), 4):
        for column, card in zip(st.columns(4), cards[row_start:row_start + 4]):
            with column.container(border=True):
                st.markdown(f"**{card['icon']} {card['name']}**")
                st.metric(card["label"], card["value"])
                ui.status_badge(not card["alerts"])
                st.page_link(card["page"], label="Open page", icon=":material/arrow_forward:")

    with ui.card("Alert log"):
        log = alert_log.table()
        if log:
            st.dataframe(log, hide_index=True)
        else:
            st.caption("No alerts yet this session. Switch on an event in Demo Controls to raise one.")


live_overview()
