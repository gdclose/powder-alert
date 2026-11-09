"""Personal forecast defaults. Recipient details live outside the repository."""
from pathlib import Path
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
CONFIG_DIR = Path.home() / ".config" / "powder-alert"
CONFIG_FILE = CONFIG_DIR / "config.json"
DATA_DIR = Path.home() / "Library" / "Application Support" / "PowderAlert"
MODELS = {"GFS": "gfs_seamless", "ECMWF": "ecmwf_ifs025", "ICON": "icon_seamless"}
RESORTS = {
    "mt_bachelor": {"name": "Mt. Bachelor · base", "lat": 43.9889, "lon": -121.6847, "elevation": 1920},
    "bend": {"name": "Bend · 97703", "lat": 44.079, "lon": -121.343, "elevation": 1090},
}
WEATHER_CODES = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Freezing fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Freezing drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers",
    85: "Snow showers", 86: "Heavy snow showers", 95: "Thunderstorms",
    96: "Thunderstorms / hail", 99: "Thunderstorms / hail",
}
