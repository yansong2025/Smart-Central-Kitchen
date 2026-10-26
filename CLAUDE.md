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
open the changed page in a browser and switch its scenario on in the sidebar.

## Layout

```
app.py                    entry point: logo, grouped navigation, sidebar "Scenario simulator"
ui.py                     shared UI helpers (header, KPI row, cards, charts, badges)
views/                    one file per page (UI only); present.py is the full-screen twin
sim/                      simulated data (no UI), one module per system
  clock.py                shared helpers: timeline, wave, rand, shift_progress
  events.py               demo events switched on from the sidebar
  alert_log.py            session log of alerts: raised, acknowledged, resolved
  systems.py              the seven systems = page registry + Overview cards
  layout.py               kitchen floor plan and AMR route (used by the 3D twin)
  temperature.py forming.py quality.py duck_oven.py amr.py forecast.py foh_robot.py
twin/                     3D digital twins (kitchen, and the FOH dining room)
  __init__.py             kitchen_twin(now, focus) and dining_twin(now): build the state in Python
  models.js               the detailed 3D models (machines, robots, people, floors)
  kitchen.js              the scene: lighting, camera, effects, inspector, toolbar
  inspector.css           styles for the panels drawn over the 3D view
static/vendor/            three.js r170 + OrbitControls, RoundedBoxGeometry, RoomEnvironment (offline)
static/fonts/             Inter variable font, served locally (offline)
assets/style.css          the design system: tokens, cards, KPI tiles, pills, alerts
assets/logo.svg           sidebar logo (and logo-mark.svg for the collapsed sidebar and tab)
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
page has its own dining-room twin, drawn by the same `kitchen.js`. The Overview
has a "Central kitchen / Front of house" switch (`twin_space`) that shows either
twin at full size; there `dining_twin(link_page=True)` adds an "Open page"
button to the FOH Service Robot page. Its "Full screen" button opens
`views/present.py`: only the twin, filling the window (`fill=` in
`kitchen_twin` / `dining_twin` sizes it to `100vh` minus the top bar), with the
sidebar and header hidden and a toolbar button that takes the browser full screen.

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
  with `events.alert(key, message, impact, action, severity="critical")`. Use
  `severity="notice"` for a change that needs planning rather than repair (it
  shows blue). Impact figures (kg, S$, pieces) are made up; `ui.alert_banner`
  marks them "(simulated)".
- **Alert workflow**: an alert is red (or blue for a notice) with an Acknowledge
  button, amber once acknowledged, and gone once resolved. `sim/alert_log.py` records this, keyed
  by the alert's `key`; a small fragment in `app.py` keeps the log current on
  every page, and the Overview shows it as a table.
- **Before/after cards** use `ui.comparison`. Their figures are illustrative
  and the helper says so under the table.
- **Events**: simulators react with `events.is_active(key)`,
  `events.intensity(key, t)` (0 to 1, ramps up then fades after switch-off) or
  `events.active_seconds(key, now)` (total time switched on).
- **Pages** start with `ui.system_header` (or `ui.page_header`), then a live
  section wrapped in `@st.fragment(run_every=ui.REFRESH_S)` holding
  `ui.alert_banner`, `ui.kpi_row([ui.kpi(...), ...])` and `ui.card(...)` blocks.
  Follow `views/forming.py`.
- **Build UI from `ui.py`, not raw Streamlit styling.** Components: `card`,
  `section`, `kpi`/`kpi_row` (with optional sparkline or bar), `facts`
  (label/value rows), `pill`/`status_pill`, `meter`, `comparison`, `twin_hint`.
  Their look lives in `assets/style.css`, which uses CSS variables in `:root`
  for every colour. A card is an `st.container` whose key starts with `card-`;
  CSS targets that key, so keep the prefix.
- **Icons are Material Symbols names** (e.g. `"conveyor_belt"`), the set
  Streamlit ships. Use `ui.icon(name)` in HTML or `:material/name:` in Streamlit
  widgets. No emoji in the UI.
- **Charts** use Altair through `ui.line_chart` or `ui.show_chart` (do not add
  Plotly); both apply the app's chart style. One measure per chart, never two
  y-axes. Blue `#2a78d6` and orange `#eb6834` for data, red `#d03b3b` dashed
  lines only for limits, grey dashed for targets.
- **Status is never colour alone**: use `ui.status_pill` (icon + text) and
  `ui.alert_banner`.
- `st.html` strips inline `<svg>`, so sparklines are SVG images
  (`ui.sparkline`). Text inside custom HTML must go through `html.escape`.
- **The twin's JavaScript only draws.** Zone positions, labels, alerts and the
  robot position are decided in Python (`twin/__init__.py`, `sim/layout.py`) and
  sent as data every refresh; `kitchen.js` updates the scene in place so the
  camera does not reset. Zone names in `sim/layout.py` must match sensor names
  in `sim/temperature.py`.
- The sidebar's **Safety zone overlay** toggle shows or hides the red Zone A
  (Duck Oven and Dim Sum Forming), amber Zone B (main CPK aisle and FOH pass),
  and blue Zone C (cold storage and hot holding) on the twins. Outlined areas
  include the surrounding equipment space and robot routes.
- **The twin is the main demo control.** Clicking a zone selects it: the camera
  glides over and an inspector panel (`twin/inspector.css`) shows its reading.
  The panel's buttons send Python a trigger: `scenario` (switch that zone's
  demo fault on or off: `SCENARIO_FOR` in `twin/__init__.py`; the callback also
  flips the sidebar switch and reruns the app) or `clicked` (open its page:
  `click_targets`, stored in `st.session_state["open_page"]`, and `app.py` does
  the `st.switch_page`).
- **Fault effects in the twin** are switched on by the zone's active scenario:
  `EFFECTS` in `kitchen.js` maps each event key to effects (`mist`, `smoke`,
  `heat`, `beacon`, `rejects`, `extra`), and each builder returns where they
  attach (`top`, `doorway`). Alert pins follow the zone's `alert` flag. The
  temperature layer colours zones by `heat` (0 safe, 1 at the limit) from
  `_heat` in `twin/__init__.py`. View buttons and layers live in `VIEWS`,
  `POSES` and `LAYERS` in `kitchen.js`.
- **Life in the twin** (all in `kitchen.js`): the whole-room views open with a
  fly-in (`glide.intro`) and fade the labels in; after `IDLE_ORBIT_S` seconds
  untouched the camera returns home and sways gently, always front-facing. Product flow: chevrons on the
  floor (`flowStrip`) and trays on the QC line stop when the forming line is
  jammed; dim sum fill the steamer-basket stack. Switching a fault off sends a
  technician (`crew`, `startResolve`) to the machine and plays a green tick
  burst; the zone's pin turns green while readings recover.
- **Inspector mini-charts**: each zone's state carries `chart` (from `_chart`
  in `twin/__init__.py`: the last 10 minutes thinned to one point per 10 s, plus
  limit/target lines and an optional `compare` series); `chartSvg` in
  `kitchen.js` draws it in the panel.
- **Keep the twin's place in the layout stable.** If the number of elements
  before a twin changes between runs, Streamlit rebuilds the twin and its
  inspector panel closes. `ui.alert_banner` always renders as one container for
  this reason; on the Overview the twin sits above the alerts.
- **3D models live in `twin/models.js`**, built from three.js shapes (no model
  files). `twin/__init__.py` joins it in front of `kitchen.js` into one module;
  `kitchen.js` calls `createModels()` and uses `kit.builders[zone.kind]` and
  `kit.robots[kind]`. A builder returns `height`, `glow`, and anchors for the
  effects (`top`, `doorway`); optional `display` (a live screen) and `andon`
  (signal tower) are updated from `kitchen.js`. Realism comes from the
  `RoomEnvironment` reflections, ACES tone mapping and contact shadows; glowing
  parts and labels use `toneMapped: false` so they stay bright.
- The vendored `OrbitControls.js`, `RoundedBoxGeometry.js` and
  `RoomEnvironment.js` each have one local edit: they import
  `./three.module.min.js` instead of `three`. Redo that if three.js is upgraded.
- Temperatures are in °C. Limits follow common food-safety practice (chilled
  0 to 5 °C, frozen at or below -18 °C, hot holding at or above 60 °C).
- Keep Python dependencies to `streamlit` (which brings pandas, numpy, Altair).
- Label anything made up as simulated in the UI; do not present figures as real
  Imperial Treasure data.

## How to add a system page

1. Create `sim/<system>.py` with the data and a `status(now)` function.
2. Create `views/<system>.py` with the UI.
3. Add the system to `SYSTEMS` in `sim/systems.py` (name, Material icon,
   navigation section, page, sim). It then appears in the navigation and on
   the Overview.
4. Run `smoke_test.py`. It reads `SYSTEMS`, so the new page is covered automatically.

## How to add a demo event

1. Add an entry to `EVENTS` in `sim/events.py` with a label and the system name.
   The sidebar toggle appears automatically under that system.
2. React to it in the simulator, and add an alert message in `status(now)` so
   the Overview and the smoke test pick it up.
3. To trigger it from the 3D twin, map the zone (or robot) name to the event
   key in `SCENARIO_FOR` in `twin/__init__.py`.

## How to add a close-up of a zone

Add a camera preset to `CAMERAS` in `twin/kitchen.js`, then call
`kitchen_twin(now, focus="<preset>")` on the page.
A preset with `fitWidth` backs the camera off until that many metres fit
across the view, so the whole floor shows at any card width (the Overview
uses this).

## How to add a zone to the 3D twin

1. Add it to `ZONES` in `sim/layout.py`. Reuse an existing `kind`, or add a new
   builder to `builders` in `twin/kitchen.js`.
2. To show live data on it, set `"system"` to a system name, or give it the
   same name as a temperature sensor. Either one also makes it clickable.
