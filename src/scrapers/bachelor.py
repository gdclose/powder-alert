"""Read Bachelor CMS reports; never present stale data as live status."""
import logging
from datetime import datetime, timedelta
from ..forecast.models import get_json

BASE = "https://cms.mtbachelor.com/jsonapi/"
REPORT_URL = "https://www.mtbachelor.com/the-mountain/lift-trail-report/"
log = logging.getLogger(__name__)

def parse_time(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo else None
    except (AttributeError, ValueError, TypeError):
        return None

def fresh(value, now, hours=36):
    timestamp = parse_time(value)
    return bool(timestamp and -timedelta(minutes=5) <= now - timestamp <= timedelta(hours=hours))

def parse_lifts(payload, now):
    lifts = []
    for item in payload.get("data", []):
        attrs = item.get("attributes", {})
        if attrs.get("season") != "winter":
            continue
        status = str(attrs.get("status", "unknown")).replace("_", " ")
        lifts.append({"name": attrs.get("name", "Unknown lift"), "status": status,
                      "updated": attrs.get("changed"),
                      "stale": not fresh(attrs.get("changed"), now)})
    return sorted(lifts, key=lambda lift: lift["name"])

def parse_snow(payload, primary_ids, now):
    candidates = []
    for item in payload.get("data", []):
        location = item.get("relationships", {}).get("location", {}).get("data") or {}
        if location.get("id") not in primary_ids:
            continue
        attrs = item.get("attributes", {})
        # date is validity; changed may be a later bulk-import timestamp.
        timestamp = parse_time(attrs.get("date"))
        if timestamp and timestamp <= now + timedelta(minutes=5):
            candidates.append((timestamp, attrs))
    if not candidates:
        return None
    _, latest = max(candidates, key=lambda pair: pair[0])
    return {"updated": latest["date"], "stale": not fresh(latest["date"], now),
            "new_snow_24h": latest.get("amount"), "base_depth": latest.get("base_depth")}

def fetch_conditions(now):
    result = {"checked": now.isoformat(), "source": REPORT_URL, "lifts": [], "snow": None}
    try:
        result["lifts"] = parse_lifts(get_json(BASE + "dor_lift/dor_lift", {"page[limit]": 50}), now)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        log.warning("Bachelor lift report unavailable: %s", exc)
    try:
        locations = get_json(BASE + "dor_reporting_location/dor_reporting_location")
        primary_ids = {x["id"] for x in locations.get("data", [])
                       if x.get("attributes", {}).get("primary") is True}
        if not primary_ids:
            return result
        payload = get_json(BASE + "dor_snow_report/dor_snow_report", {
            "sort": "-date", "page[limit]": 20,
        })
        result["snow"] = parse_snow(payload, primary_ids, now)
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        log.warning("Bachelor snow report unavailable: %s", exc)
    return result
