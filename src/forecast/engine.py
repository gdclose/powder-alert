"""Three-model blend, daily outlook and complete rolling snowfall windows.

Ranges show min/max of available model totals, not calibrated probabilities.
Models are equally weighted until observed accuracy can be validated.
"""
from collections import Counter
from datetime import datetime, timedelta
from math import isfinite
from statistics import mean
from ..config import PACIFIC, RESORTS, WEATHER_CODES
from .models import fetch_model_data
from ..scrapers.bachelor import fetch_conditions

def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)

def summary(values):
    valid = [v for v in values if numeric(v)]
    return {"mean": round(mean(valid), 1), "low": round(min(valid), 1),
            "high": round(max(valid), 1), "models": len(valid)} if valid else None

def value_at(data, key, index):
    values = data.get(key, [])
    return values[index] if index < len(values) else None

def blend_forecasts(model_data, weights=None):
    # Date joins prevent unequal model horizons from causing index errors.
    by_date = {}
    for name, payload in model_data.items():
        if not payload:
            continue
        daily = payload.get("daily", {})
        for i, timestamp in enumerate(daily.get("time", [])):
            date = datetime.fromtimestamp(timestamp, PACIFIC).date().isoformat()
            by_date.setdefault(date, {})[name] = {
                field: value_at(daily, key, i) for field, key in {
                    "temp_max": "temperature_2m_max", "temp_min": "temperature_2m_min",
                    "snowfall": "snowfall_sum", "gust": "wind_gusts_10m_max", "code": "weather_code",
                }.items()
            }
    days = []
    for date, models in sorted(by_date.items()):
        day = {"date": date}
        for field in ("temp_max", "temp_min", "snowfall", "gust"):
            day[field] = summary([m[field] for m in models.values()])
        codes = [m["code"] for m in models.values() if numeric(m["code"])]
        day["weather_desc"] = WEATHER_CODES.get(Counter(codes).most_common(1)[0][0], "Unknown") if codes else "Unavailable"
        days.append(day)
    return days

def rolling_windows(model_data, now):
    # Hourly snowfall is the preceding hour's accumulation. Include (start, end].
    start = int(now.timestamp()) // 3600 * 3600
    windows = []
    for hours in (24, 48, 72):
        per_model = {}
        gusts, temps, codes = [], [], []
        wanted = set(range(start + 3600, start + hours * 3600 + 1, 3600))
        for name, payload in model_data.items():
            if not payload:
                continue
            hourly = payload.get("hourly", {})
            rows = {t: i for i, t in enumerate(hourly.get("time", []))}
            if not wanted.issubset(rows):
                continue
            snow = [value_at(hourly, "snowfall", rows[t]) for t in sorted(wanted)]
            if not all(numeric(v) for v in snow):
                continue  # Never count a missing tail as zero snowfall.
            per_model[name] = round(sum(snow), 3)
            for t in sorted(wanted):
                i = rows[t]
                gusts.append(value_at(hourly, "wind_gusts_10m", i))
                temps.append(value_at(hourly, "temperature_2m", i))
                codes.append(value_at(hourly, "weather_code", i))
        valid_codes = [c for c in codes if numeric(c)]
        windows.append({
            "hours": hours, "start": datetime.fromtimestamp(start, PACIFIC).isoformat(),
            "end": datetime.fromtimestamp(start + hours * 3600, PACIFIC).isoformat(),
            "snow": summary(list(per_model.values())), "by_model": per_model,
            "gust": summary(gusts), "temperature": summary(temps),
            "weather": WEATHER_CODES.get(Counter(valid_codes).most_common(1)[0][0], "Unknown") if valid_codes else "Unavailable",
        })
    return windows

def build_briefing(now=None):
    now = (now or datetime.now(PACIFIC)).astimezone(PACIFIC)
    locations = {}
    for point_id, point in RESORTS.items():
        raw = fetch_model_data(point_id)
        windows = rolling_windows(raw, now)
        daily = blend_forecasts(raw)
        locations[point_id] = {
            **point, "windows": windows,
            "daily": [d for d in daily if d["date"] >= now.date().isoformat()][:10],
            "available_models": [name for name, data in raw.items() if data],
            "raw": raw,
        }
        if not windows[0]["snow"]:
            raise RuntimeError(f"No complete next-24-hour forecast for {point['name']}; no texts sent")
    return {"generated": now.isoformat(), "locations": locations, "conditions": fetch_conditions(now)}

def snow_range(data):
    if data is None:
        return "unavailable"
    def amount(value):
        # Some models return tiny negative floating-point snow amounts.
        return f"{max(0, value):.1f}".rstrip("0").rstrip(".")
    low, high = amount(data["low"]), amount(data["high"])
    text = low if low == high else low + "–" + high
    if data["models"] == 1:
        text = amount(data["mean"]) + " in (1 model)"
    else:
        text += " in"
    return text

def number(data, field="mean"):
    return f'{data[field]:.0f}' if data is not None else "?"

def format_detailed_message(briefing):
    now = datetime.fromisoformat(briefing["generated"]).astimezone(PACIFIC)
    lines = ["POWDER ALERT · " + now.strftime("%a %b %d, %I:%M %p %Z")]
    for point_id, point in briefing["locations"].items():
        lines += ["", point["name"].upper()]
        if point_id == "mt_bachelor":
            lines.append("New snow from " + datetime.fromisoformat(point["windows"][0]["start"]).astimezone(PACIFIC).strftime("%I:%M %p %Z") + " (cumulative):")
        else:
            lines.append("New snow (cumulative from current hour):")
        for window in point["windows"]:
            lines.append(f'  {window["hours"]}h: {snow_range(window["snow"])}')
        first = point["windows"][0]
        lines.append(f'Next 24h: {first["weather"]}; {number(first["temperature"], "low")}–{number(first["temperature"], "high")} F; gusts up to {number(first["gust"], "high")} mph.')
        lines.append("Models: " + ", ".join(point["available_models"]))
    conditions = briefing["conditions"]
    lines += ["", "BACHELOR RESORT REPORT"]
    snow = conditions["snow"]
    if snow and not snow["stale"]:
        lines.append(f'Reported 24h snow: {snow["new_snow_24h"] if snow["new_snow_24h"] is not None else "?"} in; base: {snow["base_depth"] if snow["base_depth"] is not None else "?"} in.')
        lines.append("Snow report dated " + snow["updated"])
    else:
        lines.append("Snow report unavailable or older than 36h.")
    lifts = conditions["lifts"]
    fresh_lifts = [lift for lift in lifts if not lift["stale"]]
    if fresh_lifts:
        counts = Counter(lift["status"] for lift in fresh_lifts)
        lines.append("Lift feed: " + ", ".join(f"{count} {status}" for status, count in sorted(counts.items())))
        for lift in fresh_lifts:
            lines.append(f'  {lift["name"]}: {lift["status"]} (updated {lift["updated"]})')
    if len(fresh_lifts) != len(lifts) or not lifts:
        lines.append("Some/all lift updates unavailable or older than 36h; check resort report.")
    lines.append("Checked " + datetime.fromisoformat(conditions["checked"]).astimezone(PACIFIC).strftime("%I:%M %p %Z"))
    lines.append(conditions["source"])
    for point in briefing["locations"].values():
        lines += ["", point["name"].upper() + " · 10-DAY OUTLOOK"]
        for day in point["daily"]:
            date = datetime.fromisoformat(day["date"]).strftime("%a %m/%d")
            lines.append(f'{date}: {day["weather_desc"]}, {number(day["temp_min"])}–{number(day["temp_max"])} F; snow {snow_range(day["snowfall"])}')
    lines += ["", "Snow ranges = model spread, not probability bounds. Fewer models at longer leads.",
              "Daily totals use Pacific calendar days; 24/48/72h totals use rolling hours.",
              "Mountain values are base-elevation forecasts; winds aloft may differ.",
              "Data: Open-Meteo (CC BY 4.0) · https://open-meteo.com/ · Mt. Bachelor",
              "Local personal forecast; verify resort operations before leaving."]
    return "\n".join(lines)

def outlook_signal(point):
    days = point["daily"]
    available = [d for d in days if d["snowfall"] is not None]
    if not available:
        return "10-day: outlook unavailable."
    # A simple signal from model means, not a ski-quality recommendation.
    signals = [i for i, day in enumerate(days)
               if day["snowfall"] and day["snowfall"]["mean"] >= 0.5]
    if not signals:
        return "10-day: limited snow signal in the model blend."
    groups = []
    for index in signals:
        if groups and index == groups[-1][-1] + 1:
            groups[-1].append(index)
        else:
            groups.append([index])
    labels = []
    for group in groups:
        def label(index):
            return datetime.fromisoformat(days[index]["date"]).strftime("%a %-m/%-d")
        labels.append(label(group[0]) if len(group) == 1 else
                      label(group[0]) + "–" + label(group[-1]))
    return "10-day snow signals: " + ", ".join(labels) + "."

def format_message(briefing):
    """Compact phone briefing; the dashboard retains the full daily tables."""
    now = datetime.fromisoformat(briefing["generated"]).astimezone(PACIFIC)
    mountain = briefing["locations"]["mt_bachelor"]
    bend = briefing["locations"]["bend"]
    first = mountain["windows"][0]
    start = datetime.fromisoformat(first["start"]).astimezone(PACIFIC)
    lines = [
        "🏔 POWDER ALERT",
        now.strftime("%a %b %-d · %-I:%M %p %Z"),
        "",
        "BACHELOR · BASE",
        f'{first["weather"]} · {number(first["temperature"], "low")}–{number(first["temperature"], "high")}°F',
        "Snow 24 / 48 / 72h: " + " / ".join(
            snow_range(w["snow"]).replace(" in", "″") for w in mountain["windows"]),
        "Cumulative from " + start.strftime("%-I:%M %p %Z") + " · model ranges",
        f'Gusts up to {number(first["gust"], "high")} mph' +
        (" ⚠" if first["gust"] and first["gust"]["high"] >= 45 else ""),
    ]
    conditions = briefing["conditions"]
    snow = conditions["snow"]
    if snow and not snow["stale"]:
        def reported(value):
            try:
                return f"{max(0, float(value)):g}"
            except (TypeError, ValueError):
                return "?"
        stamp = datetime.fromisoformat(snow["updated"]).astimezone(PACIFIC).strftime("%-m/%-d %-I:%M %p")
        lines.append(f'Resort snow: {reported(snow["new_snow_24h"])}″ past 24h · {reported(snow["base_depth"])}″ base (as of {stamp})')
    else:
        lines.append("Resort snow: report pending/stale.")
    lifts = conditions["lifts"]
    current = [lift for lift in lifts if not lift["stale"]]
    if current:
        counts = Counter(lift["status"] for lift in current)
        status = " · ".join(f"{count} {name}" for name, count in sorted(counts.items()))
        if len(current) < len(lifts):
            status += " · others stale"
        lines.append("Lifts: " + status + ".")
    else:
        lines.append("Lifts: awaiting a fresh resort update.")
    lines += [outlook_signal(mountain), "", "BEND · 97703"]
    near = bend["windows"][0]
    lines.append(f'{near["weather"]} · {number(near["temperature"], "low")}–{number(near["temperature"], "high")}°F · gusts {number(near["gust"], "high")} mph')
    if all(w["snow"] and w["snow"]["high"] == 0 for w in bend["windows"]):
        lines.append("No new snow in the next 72h model blend.")
    else:
        lines.append("Snow 24 / 48 / 72h: " + " / ".join(
            snow_range(w["snow"]).replace(" in", "″") for w in bend["windows"]))
    lines += ["", "Full outlook + lift details in your local dashboard.",
              "Weather: Open-Meteo (CC BY 4.0) · open-meteo.com · Resort: Mt. Bachelor"]
    return "\n".join(lines)

def format_forecast_message(resort_id="mt_bachelor"):
    return format_message(build_briefing())

if __name__ == "__main__":
    print(format_forecast_message())
