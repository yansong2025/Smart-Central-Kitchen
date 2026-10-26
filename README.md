# Smart Central Production Kitchen

A live dashboard demo of a "smart" central kitchen for a restaurant group: seven
connected systems, a 3D digital twin of the kitchen floor, and one-click fault
scenarios to show how operators would see and handle problems.

Built with Streamlit and three.js as a class proof of concept.

> **All data is simulated.** Nothing here comes from real equipment or from
> Imperial Treasure. Every figure (temperatures, output, costs, before/after
> comparisons) is made up for the demo. This project is not affiliated with or
> endorsed by Imperial Treasure.

![Overview page with the kitchen digital twin and a live alert](docs/overview.png)

## What it shows

| Page | What you see | Fault you can trigger |
|---|---|---|
| **Overview** | Headline numbers, 3D kitchen twin, live alerts, alert log | Shows every system's alerts |
| **Dim Sum Forming Machine** | Throughput, piece weight spread, batch and hopper status | Forming line jam |
| **AI Quality Check** | Pass rate, defects by type, latest trays inspected | Defect spike from a worn mould |
| **Smart Duck Oven** | Roast cycle phases, oven vs recipe temperature, core temperature | Oven door seal leak |
| **IoT Temperature Monitoring** | Six cold and hot zones with safe limits | Chiller door left open, freezer fault |
| **AMR Robot** | Delivery robot moving through the kitchen, next stops, battery | Aisle blocked |
| **Demand Forecast** | 14 days of orders, 7-day forecast, tomorrow's production plan | Large banquet order |
| **FOH Service Robot** | 3D dining room with a serving robot, order queue, wait times | Lunch rush |

![FOH Service Robot page with the 3D dining room](docs/foh-robot.png)

## Features

- **Interactive 3D digital twin.** Click any machine and the camera glides to
  it, with a panel showing its live reading and buttons to simulate its fault,
  resolve it, or open its page. Each fault looks different: cold mist pours
  from an open chiller, a jammed line stops with a spinning warning beacon,
  the leaking oven glows, rejected trays drop into a bin, a fallen crate blocks
  the robot, and stock piles up for a banquet or a lunch rush. Alert pins float
  above any zone in trouble, and the camera flies to a new alert by itself.
- **Kitchen and front of house.** On the Overview, switch the twin between the
  central kitchen and the restaurant dining room with its serving robot.
- **A living kitchen.** The twin opens with a camera fly-in, product flow
  arrows run along the production line, dim sum fill steamer baskets, trays
  pass through the AI inspection tunnel, and staff move around. Fixing a fault
  sends a technician to the machine and ends with a green tick. Left alone, the
  camera sways gently from side to side, always facing the front.
- **Twin toolbar.** Jump to a view (whole kitchen, cold rooms, production, the
  robot), switch layers (status, a temperature heat map, safety zones), and
  hover over a machine to see its reading.
- **Safety zone overlay.** Use the sidebar toggle to show or hide the red
  thermal/mechanical zone, amber robot traffic corridors, and blue IoT
  environmental telemetry zone on the kitchen and dining-room twins. Colored
  outlines mark the wider safety areas around the equipment and robot routes.
- **Scenario simulator.** Sidebar switches trigger each fault. Switch one on and
  the charts, alerts and twin react within seconds; switch it off and the
  system recovers.
- **Alerts that explain themselves.** Each alert says what is wrong, what it
  puts at risk, and what staff should do.
- **Acknowledge workflow.** An operator can acknowledge an alert, and the
  Overview keeps a log of when each alert was raised, acknowledged and resolved.
- **Presentation mode.** Larger text and no Streamlit toolbar, for projecting.
- **Modern operations-console design.** Grouped navigation, KPI tiles with
  live sparklines, alert cards, and a consistent light theme with the Inter font.
- **Works offline.** three.js and the font are included in the repo, so no
  internet is needed once the Python packages are installed.

![Smart Duck Oven page with roast cycle, temperature chart and 3D close-up](docs/duck-oven.png)

## Run it

You need Python 3.10 or newer.

```bash
git clone https://github.com/yansong2025/Smart-Central-Kitchen.git
cd Smart-Central-Kitchen

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # Windows: .venv\Scripts\pip
.venv/bin/streamlit run app.py                # Windows: .venv\Scripts\streamlit
```

The app opens at http://localhost:8501.

## Giving the demo

Everything happens on the 3D twin, so the audience watches one place.

1. Start on **Overview**. Everything is green.
2. Click **Chiller 1** on the twin. The camera glides over and a panel shows
   its live temperature.
3. Press **Simulate: Chiller door left open**. Within a few seconds the door
   swings open, the chiller turns red, its temperature climbs past 5 °C and an
   alert appears below the twin with the stock at risk and the action to take.
4. Press **Open page** to show the temperature chart on IoT Temperature
   Monitoring, or **Resolve fault** to watch it recover.
5. Repeat with any machine: the dim sum forming line, the duck oven, the AI
   quality check, the AMR robot, Dispatch (a banquet order), or the kitchen
   pass on the FOH Service Robot page (a lunch rush).
6. Scroll to the **Alert log** on the Overview to show the full history.

The sidebar's scenario simulator mirrors the twin and can switch any fault on
or off too; **Reset all scenarios** clears everything.

For projecting, press **Full screen** on the Overview's digital twin. Only the
3D twin is shown, filling the screen, with a switch between the central kitchen
and the front of house; the **Full screen** button in the 3D toolbar also hides
the browser's own bars (press Esc to leave), and **Exit** returns to the
Overview. For the other pages, **Presentation mode** in the sidebar enlarges
the text.

## How it works

```
app.py            navigation and the sidebar scenario simulator
ui.py             shared components: cards, KPI tiles, alerts, charts
assets/           design system stylesheet and logo
ui.py             shared page elements: headers, cards, charts, alert banners
views/            one file per page
sim/              one simulator per system, plus events and the alert log
twin/             3D twins: Python builds the scene state, kitchen.js draws it
static/           three.js (MIT licence) and the Inter font (OFL), served locally
smoke_test.py     headless check of every page and event
```

Every simulator is a plain function of the clock: given the current time and
which events are switched on, it returns the readings. There is no database
and no stored history, so every page always agrees and a restart loses nothing
but the alert log.

The 3D scenes contain no model files. The kitchen, dining room and robots are
assembled in code from boxes, cylinders and spheres.

To check everything still works after a change:

```bash
.venv/bin/python smoke_test.py    # about 40 seconds
```

[CLAUDE.md](CLAUDE.md) has the conventions and step-by-step notes for adding a
page, a demo event, or a zone on the twin.

## Built with

- [Streamlit](https://streamlit.io) for the app and pages
- [Altair](https://altair-viz.github.io) for charts
- [three.js](https://threejs.org) for the 3D twins
- pandas and NumPy for the simulated data
