"""Headless check that every page renders and every demo event raises an alert.

Run with:  .venv/bin/python smoke_test.py   (takes about 40 seconds)
"""

import time
from pathlib import Path

from streamlit.testing.v1 import AppTest

from sim.events import EVENTS
from sim.systems import SYSTEMS

APP = str(Path(__file__).parent / "app.py")
PAGES = ["views/overview.py"] + [system["page"] for system in SYSTEMS]


def check_pages(app, note):
    for page in PAGES:
        app.switch_page(page).run()
        assert not app.exception, f"{page} failed {note}: {app.exception[0].value}"
    print(f"All {len(PAGES)} pages render {note}")


app = AppTest.from_file(APP, default_timeout=30).run()
check_pages(app, "with no events")

for key in EVENTS:
    app.sidebar.toggle(key=f"event_{key}").set_value(True).run()
print(f"Switched on {len(EVENTS)} events, waiting 30 s for them to take effect...")
time.sleep(30)

check_pages(app, "with every event on")
app.switch_page("views/overview.py").run()
alerts = [error.value for error in app.error]
for system in SYSTEMS:
    assert any(system["name"] in alert for alert in alerts), f"No alert shown for {system['name']}"
print(f"Every system shows an alert on the Overview ({len(alerts)} alerts)")

app.run()  # one more run so the alert log has recorded the alerts and offers Acknowledge
[button for button in app.button if button.label == "Acknowledge"][0].click().run()
assert not app.exception, f"Acknowledge failed: {app.exception[0].value}"
assert any("Acknowledged at" in warning.value for warning in app.warning), "Acknowledged alert is not shown"
print("Acknowledging an alert works")

[button for button in app.sidebar.button if button.label == "Reset all events"][0].click().run()
assert not any(app.sidebar.toggle(key=f"event_{key}").value for key in EVENTS), "Reset did not switch the toggles off"
print("Reset all events works")

app.sidebar.toggle(key="presentation").set_value(True).run()
assert not app.exception, "Presentation mode failed"
print("Presentation mode works")
