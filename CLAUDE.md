# Imperial Treasure Smart Central Production Kitchen

A proof-of-concept dashboard for a class demo. It is a Streamlit multipage app
and **all data is simulated in Python**: no database, no APIs, no real devices.

The priority is code a classmate can read in one sitting. Prefer the simple,
obvious version over a clever or general one.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # first time
.venv/bin/streamlit run app.py
.venv/bin/python smoke_test.py    # headless check of every page and event (~40 s)
```

Run the smoke test after any change. It does not check how pages look, so also
open the changed page in a browser and switch its Demo Controls event on.

## Layout

```
app.py                    entry point: navigation + sidebar "Demo Controls"
ui.py                     shared UI helpers (header, KPI row, cards, charts, badges)
views/                    one file per page (UI only)
sim/                      simulated data (no UI), one module per system
  clock.py                shared helpers: timeline, wave, rand, shift_progress
  events.py               demo events switched on from the sidebar
  alert_log.py            session log of alerts: raised, acknowledged, resolved
  systems.py              the seven systems = page registry + Overview cards
  layout.py               kitchen floor plan and AMR route (used by the 3D twin)
  temperature.py forming.py quality.py duck_oven.py amr.py forecast.py foh_robot.py
twin/                     3D digital twins (kitchen, and the FOH dining room)
  __init__.py             kitchen_twin(now, focus) and dining_twin(now): build the state in Python
  kitchen.js              three.js scene that draws that state (the only JS)
static/vendor/            three.js r170 + OrbitControls, served locally (offline)
assets/style.css          a few CSS touches on top of the theme
assets/presentation.css   extra CSS for the sidebar's "Presentation mode" toggle
.streamlit/config.toml    light theme, static file serving
smoke_test.py
```

Pages live in `views/`, not `pages/`, because navigation is defined explicitly
with `st.navigation` in `app.py`.

## Pages and their demo events

| Page | View / simulator | Demo event |
|---|---|---|
| Overview | `views/overview.py` | shows every system's alerts |
| Dim Sum Forming Machine | `forming` | `forming_jam` |
| AI Quality Check | `quality` | `defect_spike` |
| Smart Duck Oven | `duck_oven` | `oven_door_leak` |
| IoT Temperature Monitoring | `iot_temperature` / `temperature` | `chiller_door_open`, `freezer_fault` |
| AMR Robot | `amr` | `amr_blocked` |
| Demand Forecast | `forecast` | `banquet_order` |
| FOH Service Robot | `foh_robot` | `lunch_rush` |

The kitchen twin appears on Overview, IoT Temperature and AMR Robot, and as a
close-up on Dim Sum Forming Machine and Smart Duck Oven. The FOH Service Robot
page has its own dining-room twin, drawn by the same `kitchen.js`.

## Conventions

- **Simulated data is a function of the clock.** Simulators take `now`
  (`time.time()`) and compute values from it using `sim/clock.py` (`wave` for
  smooth drift, `rand` for repeatable randomness). No stored history and no
  `random` module, so every page and every rerun agree. The only session state
  is `st.session_state["events"]` and the sidebar toggles.
- **`sim/` has no UI; `views/` has no data logic.** `sim/events.py` and
  `sim/alert_log.py` are the only `sim` modules that touch Streamlit (for
  session state).
- **Every simulator has `status(now)`** returning
  `{"headline": (label, value), "alerts": [events.alert(...), ...]}`. The
  Overview cards, the alert feed and the twin's zone labels all come from it.
- **Every alert says what is wrong, what it costs and what to do**: build it
  with `events.alert(key, message, impact, action)`. Impact figures (kg, S$,
  pieces) are made up; `ui.alert_banner` marks them "(simulated)".
- **Alert workflow**: an alert is red with an Acknowledge button, amber once
  acknowledged, and gone once resolved. `sim/alert_log.py` records this, keyed
  by the alert's `key`; a small fragment in `app.py` keeps the log current on
  every page, and the Overview shows it as a table.
- **Before/after cards** use `ui.comparison`. Their figures are illustrative
  and the helper says so under the table.
- **Events**: simulators react with `events.is_active(key)`,
  `events.intensity(key, t)` (0 to 1, ramps up then fades after switch-off) or
  `events.active_seconds(key, now)` (total time switched on).
- **Pages** start with `ui.page_header`, then a live section wrapped in
  `@st.fragment(run_every=ui.REFRESH_S)` holding `ui.alert_banner`,
  `ui.kpi_row` and `ui.card` blocks. Follow `views/forming.py`.
- **Charts** use Altair through `ui.line_chart` where possible (do not add
  Plotly). One measure per chart, never two y-axes. Blue `#2a78d6` and orange
  `#eb6834` for data, red `#d03b3b` dashed lines only for limits, grey dashed
  for targets.
- **Status is never colour alone**: use `ui.status_badge` (icon + text) and
  `ui.alert_banner`.
- **The twin's JavaScript only draws.** Zone positions, labels, alerts and the
  robot position are decided in Python (`twin/__init__.py`, `sim/layout.py`) and
  sent as data every refresh; `kitchen.js` updates the scene in place so the
  camera does not reset. Zone names in `sim/layout.py` must match sensor names
  in `sim/temperature.py`.
- **Clicking the twin opens a page.** `kitchen.js` sends the clicked zone's
  name; `twin/__init__.py` maps it to a page (`click_targets`) and stores it in
  `st.session_state["open_page"]`; `app.py` does the `st.switch_page`.
- `static/vendor/OrbitControls.js` has one local edit: it imports
  `./three.module.min.js` instead of `three`. Redo that if three.js is upgraded.
- Temperatures are in °C. Limits follow common food-safety practice (chilled
  0 to 5 °C, frozen at or below -18 °C, hot holding at or above 60 °C).
- Keep Python dependencies to `streamlit` (which brings pandas, numpy, Altair).
- Label anything made up as simulated in the UI; do not present figures as real
  Imperial Treasure data.

## How to add a system page

1. Create `sim/<system>.py` with the data and a `status(now)` function.
2. Create `views/<system>.py` with the UI.
3. Add the system to `SYSTEMS` in `sim/systems.py` (name, icon, page, sim). It
   then appears in the navigation and on the Overview.
4. Run `smoke_test.py`. It reads `SYSTEMS`, so the new page is covered automatically.

## How to add a demo event

1. Add an entry to `EVENTS` in `sim/events.py` with a label and the system name.
   The sidebar toggle appears automatically under that system.
2. React to it in the simulator, and add an alert message in `status(now)` so
   the Overview and the smoke test pick it up.

## How to add a close-up of a zone

Add a camera preset to `CAMERAS` in `twin/kitchen.js`, then call
`kitchen_twin(now, focus="<preset>")` on the page.

## How to add a zone to the 3D twin

1. Add it to `ZONES` in `sim/layout.py`. Reuse an existing `kind`, or add a new
   builder to `builders` in `twin/kitchen.js`.
2. To show live data on it, set `"system"` to a system name, or give it the
   same name as a temperature sensor. Either one also makes it clickable.
