# Powder Alert

SMS-based ski resort weather forecasts. Get personalized point forecasts texted to you daily — no app to download, no notifications to manage.

## What It Does

- Blends multiple weather models (GFS, ECMWF, ICON) for accurate point forecasts
- Sends daily SMS briefings with snow, wind, and lift conditions
- Tracks model accuracy over time to weight the most reliable source
- Covers specific ski resort locations (starting with Mt. Bachelor, OR)

## How It Works

```
Open-Meteo API (GFS/ECMWF/ICON)
        ↓
  Model Blending Engine
        ↓
  Forecast Formatter
        ↓
  Twilio SMS Delivery
        ↓
  Your phone at 7am ☀️🏔️
```

## Tech Stack

- **Python 3.11+** — forecast engine and model blending
- **Open-Meteo API** — free weather model data (GFS, ECMWF, ICON)
- **Twilio** — SMS delivery
- **Playwright** — resort condition scraping (wind sensors, lift status)
- **Cloud Run** — scheduled execution (cron)
- **Stripe** — subscription billing (planned)

## Project Structure

```
powder-alert/
├── src/
│   ├── forecast/
│   │   ├── __init__.py
│   │   ├── engine.py          # Multi-model blending engine
│   │   ├── models.py          # Weather model fetchers
│   │   └── accuracy.py        # Model accuracy tracking
│   ├── scrapers/
│   │   ├── __init__.py
│   │   └── bachelor.py        # Mt Bachelor conditions scraper
│   ├── delivery/
│   │   ├── __init__.py
│   │   └── sms.py             # Twilio SMS sender
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py             # Sign-up API (FastAPI)
│   └── config.py              # Configuration and resort definitions
├── tests/
│   ├── test_engine.py
│   ├── test_models.py
│   └── test_sms.py
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

## Supported Resorts

| Resort | Location | Status |
|--------|----------|--------|
| Mt. Bachelor | Bend, OR | Active |
| More coming... | | Planned |

## Getting Started

```bash
# Clone the repo
git clone https://github.com/garrett-cyber/powder-alert.git
cd powder-alert

# Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Twilio credentials and phone number

# Run a forecast
python -m src.forecast.engine
```

## Roadmap

- [ ] Twilio SMS delivery (replacing iMessage/AppleScript)
- [ ] Sign-up page and user management
- [ ] Multi-resort support
- [ ] Stripe subscription billing
- [ ] Powder day alerts (threshold-based)
- [ ] 3-day outlook vs daily forecast options
- [ ] Cloud Run deployment with cron scheduling

## Background

Built this originally as a personal tool to get Mt. Bachelor forecasts via iMessage every morning. Blends GFS, ECMWF, and ICON models with confidence scoring and tracks which model performs best over a 30-day rolling window. Now turning it into a service others can subscribe to.

## License

MIT
