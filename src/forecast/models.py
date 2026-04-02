"""Fetch forecast data from multiple weather models via Open-Meteo API."""

import requests
from typing import Dict, Optional
from ..config import MODELS, RESORTS


def fetch_model_data(resort_id: str = "mt_bachelor") -> Dict:
    """Fetch forecast data from all configured weather models.

    Returns dict keyed by model name with hourly/daily forecast data.
    """
    resort = RESORTS[resort_id]
    url = "https://api.open-meteo.com/v1/forecast"
    model_data = {}

    for model_name, model_id in MODELS.items():
        params = {
            "latitude": resort["lat"],
            "longitude": resort["lon"],
            "models": model_id,
            "hourly": "temperature_2m,precipitation,snowfall,wind_speed_10m,wind_direction_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum,wind_speed_10m_max,weather_code",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "forecast_days": 14,
            "timezone": "America/Los_Angeles",
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            model_data[model_name] = resp.json()
        except requests.RequestException as e:
            print(f"Failed to fetch {model_name}: {e}")
            model_data[model_name] = None

    return model_data


def fetch_resort_snow(resort_id: str = "mt_bachelor") -> Optional[Dict]:
    """Fetch current snow report from resort API."""
    resort = RESORTS[resort_id]
    api_url = resort.get("cms_api")
    if not api_url:
        return None

    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data"):
            attrs = data["data"][0].get("attributes", {})
            return {
                "new_snow_12h": attrs.get("field_new_snow_12_hours"),
                "new_snow_24h": attrs.get("field_new_snow_24_hours"),
                "new_snow_72h": attrs.get("field_new_snow_72_hours"),
                "base_depth": attrs.get("field_base_depth"),
                "season_total": attrs.get("field_season_snowfall"),
            }
    except requests.RequestException:
        pass
    return None
