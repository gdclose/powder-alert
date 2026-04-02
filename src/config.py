"""Resort definitions and configuration."""

import os
from dotenv import load_dotenv

load_dotenv()

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Delivery
SEND_TO_PHONE = os.getenv("SEND_TO_PHONE")
TIMEZONE = os.getenv("TIMEZONE", "America/Los_Angeles")

# WMO Weather Codes
WEATHER_CODES = {
    0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 48: "Freezing Fog",
    51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
    56: "Freezing Drizzle", 57: "Heavy Freezing Drizzle",
    61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
    66: "Freezing Rain", 67: "Heavy Freezing Rain",
    71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 77: "Snow Grains",
    80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
    85: "Light Snow Showers", 86: "Heavy Snow Showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ Hail", 99: "Heavy Thunderstorm",
}

# Resort definitions
RESORTS = {
    "mt_bachelor": {
        "name": "Mt. Bachelor",
        "lat": 43.9889,
        "lon": -121.6847,
        "elevation": 1920,  # meters (~6,300 ft base lodge)
        "type": "mountain",
        "scraper": "bachelor",
        "cms_api": "https://cms.mtbachelor.com/jsonapi/dor_snow_report/dor_snow_report",
        "liftie_url": "https://liftie.info/api/resort/mtbachelor",
    },
}

# Weather models to blend
MODELS = {
    "GFS": "gfs_seamless",
    "ECMWF": "ecmwf_ifs025",
    "ICON": "icon_seamless",
}

# Forecast days to include in outlook
FORECAST_DAYS = [1, 3, 5, 7, 10, 14]
