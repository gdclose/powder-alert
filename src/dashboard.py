"""Standalone local dashboard, regenerated with each briefing."""
from html import escape
from datetime import datetime
from .config import PACIFIC
from .forecast.engine import format_message, snow_range, number

def render_dashboard(briefing):
    cards = []
    for point in briefing["locations"].values():
        windows = "".join(
            '<article><small>THROUGH ' + str(w["hours"]) + ' HOURS</small><h2>' +
            escape(snow_range(w["snow"])) + '</h2><span>' +
            str(w["snow"]["models"] if w["snow"] else 0) + ' models · cumulative</span></article>'
            for w in point["windows"])
        rows = "".join("<tr><td>" + escape(d["date"]) + "</td><td>" + escape(d["weather_desc"]) +
                       "</td><td>" + escape(number(d["temp_min"]) + "–" + number(d["temp_max"])) +
                       " °F</td><td>" + escape(snow_range(d["snowfall"])) + "</td></tr>"
                       for d in point["daily"])
        cards.append("<section><h2>" + escape(point["name"]) + "</h2><div class='cards'>" + windows +
                     "</div><p>Snow ranges show model disagreement. Base elevation for Bachelor; a representative NW Bend point for 97703.</p>" +
                     "<h3>10-day outlook</h3><div class='scroll'><table><thead><tr><th>Date</th><th>Weather</th><th>Low–high</th><th>Daily new snow</th></tr></thead><tbody>" +
                     rows + "</tbody></table></div></section>")
    conditions = briefing["conditions"]
    lift_rows = "".join(
        "<tr><td>" + escape(lift["name"]) + "</td><td>" +
        escape(("Last known: " if lift["stale"] else "Reported: ") + lift["status"]) +
        "</td><td>" + escape(lift["updated"] or "Unknown date") +
        (" · older than 36h" if lift["stale"] else "") + "</td></tr>"
        for lift in conditions["lifts"])
    lifts = '<section><h2>Bachelor lift report</h2><p>Checked ' + escape(conditions["checked"]) + \
        ' · Reported status, not a prediction of tomorrow’s operations.</p><div class="scroll"><table>' + \
        '<thead><tr><th>Lift</th><th>Status</th><th>Source last changed</th></tr></thead><tbody>' + \
        (lift_rows or '<tr><td colspan="3">Lift feed unavailable. Check the resort report.</td></tr>') + \
        '</tbody></table></div></section>'
    updated = datetime.fromisoformat(briefing["generated"]).astimezone(PACIFIC).strftime("%a %b %d · %I:%M %p %Z")
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Powder Alert · Bachelor & Bend</title><style>
:root{font-family:system-ui,sans-serif;color:#183d32;background:#f5f5ee}*{box-sizing:border-box}
body{max-width:1120px;margin:auto;padding:28px}header{border-bottom:1px solid #b9ccc2;padding:24px 0}
h1{font:clamp(32px,6vw,58px) Georgia,serif;margin:12px 0}h2{font-family:Georgia,serif}
small,.eyebrow{letter-spacing:.12em;font-size:12px}section{padding:24px 0}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
article{background:#dcecef;border:1px solid #bdd2d3;border-radius:14px;padding:22px}article h2{font-size:28px;margin:12px 0}
span,p{font-size:14px;line-height:1.6}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;text-align:left}
th,td{padding:12px;border-bottom:1px solid #d3ded8;white-space:nowrap}th{font-size:12px}
details{background:white;padding:20px;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.7 system-ui}
a{color:#215a46}footer{padding:24px 0;font-size:13px}@media(max-width:650px){body{padding:18px}.cards{grid-template-columns:1fr}article{padding:16px}}
</style><header><div class="eyebrow">POWDER ALERT / PERSONAL EDITION</div><h1>Your mountain morning.</h1><p>""" + escape(updated) + """ · Snapshot; does not auto-refresh.</p></header>""" + "".join(cards) + lifts + '<details><summary>Full text briefing</summary><pre>' + escape(format_message(briefing)) + """</pre></details><footer>Weather: <a href="https://open-meteo.com/">Open-Meteo</a> · CC BY 4.0. Resort conditions: Mt. Bachelor.<br>Model spread is not a calibrated probability interval. Forecasts and resort reports can change.</footer></html>"""
