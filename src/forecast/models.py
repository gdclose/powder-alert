"""Open-Meteo model data, with explicit elevation, units and bounded retries."""
import json
import logging
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from ..config import MODELS, RESORTS

log = logging.getLogger(__name__)

def get_json(url, params=None):
    if params:
        url += "?" + urlencode(params)
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "PowderAlert/1.0 (personal forecast)"})
            with urlopen(request, timeout=20) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            if isinstance(exc, HTTPError) and exc.code not in (429, 500, 502, 503, 504):
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def fetch_model_data(resort_id="mt_bachelor"):
    point = RESORTS[resort_id]
    result = {}
    for name, model in MODELS.items():
        params = {
            "latitude": point["lat"], "longitude": point["lon"],
            "elevation": point["elevation"], "models": model,
            "hourly": "temperature_2m,snowfall,wind_speed_10m,wind_gusts_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,snowfall_sum,wind_gusts_10m_max,weather_code",
            "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
            "precipitation_unit": "inch", "forecast_days": 11,
            "timezone": "America/Los_Angeles", "timeformat": "unixtime",
        }
        try:
            data = get_json("https://api.open-meteo.com/v1/forecast", params)
            if not isinstance(data.get("hourly"), dict) or not isinstance(data.get("daily"), dict):
                raise ValueError("Missing hourly or daily forecast")
            result[name] = data
        except (OSError, ValueError, TypeError) as exc:
            log.warning("%s %s unavailable: %s", resort_id, name, exc)
            result[name] = None
    return result
