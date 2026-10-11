import time

import streamlit as st

import ui
from sim import duck_oven
from twin import kitchen_twin

ui.page_header(
    "🦆",
    "Smart Duck Oven",
    "Programmable oven that runs the roast-duck recipe automatically. "
    f"The demo plays one roast cycle every {duck_oven.CYCLE_S // 60} minutes.",
)


@st.fragment(run_every=ui.REFRESH_S)
def live_oven():
    now = time.time()
    history = duck_oven.temperatures(now)
    latest = history.iloc[-1]
    current = int(duck_oven.phase_index(now))
    core = duck_oven.core_temperature(now)

    ui.alert_banner(duck_oven.status(now)["alerts"], "Oven is following the recipe")
    ui.kpi_row([
        ("Oven temperature", f"{latest['actual']:.0f} °C"),
        ("Recipe temperature", f"{latest['recipe']:.0f} °C"),
        ("Ducks in oven", duck_oven.DUCKS_PER_BATCH),
        ("Ducks roasted today", f"{duck_oven.ducks_today(now):,}"),
    ])

    with ui.card("Roast cycle"):
        for i, (column, (name, _, setpoint)) in enumerate(zip(st.columns(len(duck_oven.PHASES)), duck_oven.PHASES)):
            marker = "✅ Done" if i < current else "🔥 In progress" if i == current else "⏳ Waiting"
            column.markdown(f"**{i + 1}. {name}** · {setpoint} °C  \n{marker}")
        cycle = float(duck_oven.cycle_fraction(now))
        st.progress(cycle, text=f"Cycle {cycle:.0%} complete")

    left, right = st.columns([3, 2])
    with left, ui.card("Oven temperature, last 10 minutes"):
        ui.line_chart(history, {"recipe": "Recipe", "actual": "Actual"}, "°C", key="oven_temp", height=260)
    with right, ui.card("Duck core temperature"):
        st.metric(f"Safe to serve at {duck_oven.CORE_TARGET_C} °C", f"{core:.0f} °C")
        if core >= duck_oven.CORE_TARGET_C:
            st.badge("Cooked through", icon=":material/check_circle:", color="green")
        else:
            st.badge("Still cooking", icon=":material/hourglass_top:", color="gray")
        st.progress(min(core / duck_oven.CORE_TARGET_C, 1.0), text="Progress to safe core temperature")

    left, right = st.columns([3, 2])
    with left, ui.card("On the kitchen floor"):
        kitchen_twin(now, focus="oven", height=330)
    with right, ui.card("Before and after automation"):
        ui.comparison(
            [
                ("Ducks per batch", "12", str(duck_oven.DUCKS_PER_BATCH)),
                ("Chef attention", "Watches and turns ducks all cycle", "Loads and unloads only"),
                ("Temperature control", "By eye, about ± 15 °C", "Automatic, about ± 2 °C"),
                ("Cooking record", "Paper log", "Saved automatically for every batch"),
            ],
            before="Traditional oven", after="Smart oven",
        )


live_oven()
