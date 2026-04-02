"""Multi-model blending forecast engine.

Combines GFS, ECMWF, and ICON model data with confidence scoring
to produce a single blended forecast. Tracks model accuracy over time
to weight the most reliable source.
"""

from datetime import datetime
from typing import Dict, List
from .models import fetch_model_data, fetch_resort_snow
from .accuracy import load_accuracy_weights
from ..config import WEATHER_CODES, FORECAST_DAYS, RESORTS


def blend_forecasts(model_data: Dict, weights: Dict[str, float] = None) -> List[Dict]:
    """Blend multiple model forecasts using weighted averaging.

    Args:
        model_data: Dict of model_name -> API response
        weights: Optional model weights from accuracy tracking

    Returns:
        List of daily forecast dicts with blended values
    """
    if weights is None:
        weights = {name: 1.0 for name in model_data}

    # Normalize weights
    total = sum(weights.get(m, 1.0) for m in model_data if model_data[m])
    if total == 0:
        total = 1.0

    blended_days = []
    active_models = {m: d for m, d in model_data.items() if d and "daily" in d}

    if not active_models:
        return []

    # Use first model to determine number of days
    first_model = next(iter(active_models.values()))
    num_days = len(first_model["daily"].get("time", []))

    for i in range(num_days):
        day = {"date": first_model["daily"]["time"][i]}
        fields = {
            "temp_max": "temperature_2m_max",
            "temp_min": "temperature_2m_min",
            "precip": "precipitation_sum",
            "snowfall": "snowfall_sum",
            "wind_max": "wind_speed_10m_max",
        }

        for field, api_key in fields.items():
            weighted_sum = 0
            weight_sum = 0
            for model_name, data in active_models.items():
                val = data["daily"].get(api_key, [None] * num_days)[i]
                if val is not None:
                    w = weights.get(model_name, 1.0) / total
                    weighted_sum += val * w
                    weight_sum += w
            day[field] = round(weighted_sum / weight_sum, 1) if weight_sum > 0 else None

        # Weather code: majority vote
        codes = []
        for model_name, data in active_models.items():
            code = data["daily"].get("weather_code", [None] * num_days)[i]
            if code is not None:
                codes.append(code)
        day["weather_code"] = max(set(codes), key=codes.count) if codes else None
        day["weather_desc"] = WEATHER_CODES.get(day["weather_code"], "Unknown")

        blended_days.append(day)

    return blended_days


def format_forecast_message(resort_id: str = "mt_bachelor") -> str:
    """Generate a formatted forecast message for SMS delivery."""
    resort = RESORTS[resort_id]
    model_data = fetch_model_data(resort_id)
    weights = load_accuracy_weights()
    forecast = blend_forecasts(model_data, weights)
    snow = fetch_resort_snow(resort_id)

    now = datetime.now()
    lines = [f"{resort['name']} Forecast", f"{now.strftime('%a %b %d, %Y')}", ""]

    # Current snow report
    if snow:
        lines.append("SNOW REPORT")
        if snow.get("new_snow_24h"):
            lines.append(f"  24hr: {snow['new_snow_24h']}\"")
        if snow.get("new_snow_72h"):
            lines.append(f"  72hr: {snow['new_snow_72h']}\"")
        if snow.get("base_depth"):
            lines.append(f"  Base: {snow['base_depth']}\"")
        lines.append("")

    # Forecast outlook
    if forecast:
        lines.append("FORECAST")
        for day_idx in FORECAST_DAYS:
            if day_idx < len(forecast):
                d = forecast[day_idx]
                date_str = datetime.strptime(d["date"], "%Y-%m-%d").strftime("%a %m/%d")
                snow_str = f" | {d['snowfall']}\" snow" if d.get("snowfall") and d["snowfall"] > 0 else ""
                lines.append(
                    f"  {date_str}: {d.get('temp_max', '?')}°/{d.get('temp_min', '?')}° "
                    f"{d['weather_desc']}{snow_str}"
                )

    # Model agreement
    active = [m for m, d in model_data.items() if d]
    lines.append(f"\nModels: {', '.join(active)}")

    return "\n".join(lines)


if __name__ == "__main__":
    msg = format_forecast_message()
    print(msg)
