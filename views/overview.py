import time

import streamlit as st

import ui
from sim import alert_log, clock, duck_oven, forming, systems
from twin import dining_twin, kitchen_twin

ui.page_header(
    "space_dashboard",
    "Kitchen overview",
    "Live status of the seven smart systems in the central production kitchen. All data is simulated.",
    crumb="Imperial Treasure · Central Production Kitchen",
)


def system_tile(card):
    """One system on the Overview: icon, name, status, headline number and a link to its page."""
    if not card["alerts"]:
        status = ui.pill("Running", "ok", "check_circle")
    elif all(alert_log.acknowledged_at(a["key"]) for a in card["alerts"]):
        status = ui.pill("Being handled", "warn", "engineering")
    else:
        status = ui.pill("Needs attention", "crit", "error")
    tone = "crit" if card["alerts"] else ""
    with st.container(key=f"card-system-{ui.slug(card['name'])}"):
        st.html(
            f'<div class="sys-top"><div class="sys-icon {tone}">{ui.icon(card["icon"])}</div>{status}</div>'
            f'<div class="sys-name">{card["name"]}</div>'
            f'<div class="sys-label">{card["label"]}</div><div class="sys-value">{card["value"]}</div>'
        )
        st.page_link(card["page"], label="View details", icon=":material/arrow_forward:")


@st.fragment(run_every=ui.REFRESH_S)
def live_overview():
    now = time.time()
    cards = systems.summary(now)
    alerting = [card for card in cards if card["alerts"]]
    open_alerts = [alert for card in cards for alert in card["alerts"]]
    waiting = [a for a in open_alerts if not alert_log.acknowledged_at(a["key"])]
    healthy = len(cards) - len(alerting)
    progress = clock.shift_progress(now)
    ppm = forming.throughput(now, seconds=0)["ppm"].iloc[-1]

    ui.kpi_row([
        ui.kpi("Systems healthy", healthy, unit=f"/ {len(cards)}", icon_name="health_and_safety",
               bar=healthy / len(cards), tone="crit" if alerting else "ok"),
        ui.kpi("Open alerts", len(open_alerts), icon_name="notifications",
               note=f"{len(waiting)} not yet acknowledged" if open_alerts else "Nothing needs attention",
               tone="crit" if waiting else ""),
        ui.kpi("Dim sum today", f"{forming.pieces_today(now):,}", icon_name="conveyor_belt",
               note=f"Formed · line at {ppm:.0f} pcs/min"),
        ui.kpi("Ducks today", f"{duck_oven.ducks_today(now):,}", icon_name="oven_gen",
               note=f"Roasted · {duck_oven.DUCKS_PER_BATCH} in the oven now"),
        ui.kpi("Shift progress", f"{progress:.0%}", icon_name="schedule", bar=progress,
               note=f"Shift {clock.SHIFT_START_H:02d}:00 to {clock.SHIFT_END_H:02d}:00"),
    ])

    # The twin comes first and keeps its place on the page: alerts appearing below it
    # never push it around, so the 3D view and its inspector panel stay put during a demo.
    if alerting:
        noun = "system needs" if len(alerting) == 1 else "systems need"
        status = ui.pill(f"{len(alerting)} {noun} attention", "crit")
    else:
        status = ui.pill("All systems normal", "ok")
    with ui.card("Digital twin", "Live 3D view: the central kitchen and the restaurant front of house", aside=status):
        with st.container(horizontal=True, vertical_alignment="center"):
            space = st.segmented_control(
                "View", ["Kitchen", "Dining room"], key="twin_space", default="Kitchen", label_visibility="collapsed",
                format_func=lambda name: {"Kitchen": ":material/kitchen: Central kitchen",
                                          "Dining room": ":material/room_service: Front of house"}[name],
            )
            st.space("stretch")
            if st.button("Full screen", icon=":material/fullscreen:", key="go_full_screen"):
                # Open the full-screen page on the same twin. A full rerun lets app.py switch page.
                st.session_state["present_space"] = space or "Kitchen"
                st.session_state["open_page"] = "views/present.py"
                st.rerun()
        if space == "Dining room":
            dining_twin(now, height=520, link_page=True)
        else:
            kitchen_twin(now, focus="overview", height=520)
        ui.twin_hint()

    # Live alerts: a row of alert cards, or one slim "all clear" bar.
    with st.container(key="live-alerts"):
        if open_alerts:
            ui.section("Live alerts", f"{len(open_alerts)} open · open a system's page for the full impact")
            items = [(card["name"], alert) for card in alerting for alert in card["alerts"]]
            # Up to three per row; four sit as two pairs rather than three and one.
            columns = st.columns(2 if len(items) == 4 else min(3, len(items)), gap="medium")
            for i, (system, alert) in enumerate(items):
                with columns[i % len(columns)]:
                    ui.alert_banner([alert], "", title=system, compact=True)
        else:
            ui.alert_banner([], "All systems are running normally · no open alerts")

    ui.section("Systems", f"{len(cards)} connected")
    for row_start in range(0, len(cards), 4):
        for column, card in zip(st.columns(4, gap="medium"), cards[row_start:row_start + 4]):
            with column:
                system_tile(card)

    log = alert_log.table()
    with ui.card("Alert log", "Every alert this session: when it was raised, acknowledged and resolved"):
        if log:
            st.dataframe(log, hide_index=True, column_config={
                "Raised": st.column_config.TextColumn(width="small"),
                "Alert": st.column_config.TextColumn(width="large"),
                "Resolved": st.column_config.TextColumn(width="small"),
            })
        else:
            st.html('<div class="card-sub">No alerts yet. Switch on a scenario in the sidebar to raise one.</div>')


live_overview()
