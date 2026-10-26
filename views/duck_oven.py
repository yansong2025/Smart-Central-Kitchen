import time

import streamlit as st

import ui
from sim import duck_oven
from twin import kitchen_twin

ui.system_header(
    "Smart Duck Oven",
    "Programmable oven that runs the roast-duck recipe automatically. "
    f"The demo plays one roast cycle every {duck_oven.CYCLE_S // 60} minutes.",
)


def roast_steps(current):
    """The five recipe phases as a step tracker: done, in progress, or still to come."""
    steps = []
    for i, (name, _, setpoint) in enumerate(duck_oven.PHASES):
        if i < current:
            state, mark = "done", ui.icon("check")
        elif i == current:
            state, mark = "now", ui.icon("local_fire_department")
        else:
            state, mark = "", str(i + 1)
        steps.append(f'<div class="step {state}"><div class="step-dot">{mark}</div>'
                     f'<div class="step-name">{name}</div><div class="step-temp">{setpoint} °C</div></div>')
    st.html(f'<div class="steps" style="--n:{len(steps)}">{"".join(steps)}</div>')


@st.fragment(run_every=ui.REFRESH_S)
def live_oven():
    now = time.time()
    history = duck_oven.temperatures(now)
    latest = history.iloc[-1]
    current = int(duck_oven.phase_index(now))
    core = duck_oven.core_temperature(now)
    cycle = float(duck_oven.cycle_fraction(now))
    gap = latest["recipe"] - latest["actual"]

    ui.alert_banner(duck_oven.status(now)["alerts"], "Oven is following the recipe")
    ui.kpi_row([
        ui.kpi("Oven temperature", f"{latest['actual']:.0f}", unit="°C", icon_name="thermostat",
               spark=history["actual"].tail(120), tone="crit" if gap > duck_oven.MAX_GAP_C else ""),
        ui.kpi("Recipe temperature", f"{latest['recipe']:.0f}", unit="°C", icon_name="menu_book",
               note=f"Phase: {duck_oven.PHASES[current][0]}"),
        ui.kpi("Duck core temperature", f"{core:.0f}", unit="°C", icon_name="device_thermostat",
               note=f"Safe to serve at {duck_oven.CORE_TARGET_C} °C", bar=core / duck_oven.CORE_TARGET_C,
               tone="ok" if core >= duck_oven.CORE_TARGET_C else "warn"),
        ui.kpi("Ducks roasted today", f"{duck_oven.ducks_today(now):,}", icon_name="oven_gen",
               note=f"Daily target {duck_oven.DAILY_TARGET:,}"),
    ])

    remaining = (1 - cycle) * duck_oven.CYCLE_S
    with ui.card("Roast cycle", f"{cycle:.0%} complete · {remaining // 60:.0f} min {remaining % 60:02.0f} s left in the demo cycle"):
        roast_steps(current)
        st.html(ui.meter(cycle))

    left, right = st.columns([3, 2], gap="medium")
    with left, ui.card("Oven temperature", "Actual against the recipe, last 10 minutes"):
        ui.line_chart(history, {"recipe": "Recipe", "actual": "Actual"}, "°C", key="oven_temp", height=300)
    with right, ui.card("On the kitchen floor", "Close-up of the oven on the digital twin"):
        kitchen_twin(now, focus="oven", height=300)
        ui.twin_hint()

    left, right = st.columns([3, 2], gap="medium")
    with left, ui.card("Before and after automation"):
        ui.comparison(
            [
                ("Ducks per batch", "12", str(duck_oven.DUCKS_PER_BATCH)),
                ("Chef attention", "Watches and turns ducks all cycle", "Loads and unloads only"),
                ("Temperature control", "By eye, about ± 15 °C", "Automatic, about ± 2 °C"),
                ("Cooking record", "Paper log", "Saved automatically for every batch"),
            ],
            before="Traditional oven", after="Smart oven",
        )
    with right, ui.card("This batch"):
        cooked = ui.pill("Cooked through", "ok", "check_circle") if core >= duck_oven.CORE_TARGET_C \
            else ui.pill("Still cooking", "neutral", "hourglass_top")
        ui.facts([
            ("restaurant", "Ducks in the oven", str(duck_oven.DUCKS_PER_BATCH)),
            ("menu_book", "Current phase", duck_oven.PHASES[current][0]),
            ("device_thermostat", "Core temperature", f"{core:.0f} °C"),
            ("verified", "Food safety", cooked),
        ])


live_oven()
