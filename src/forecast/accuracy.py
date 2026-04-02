"""Track weather model accuracy over a 30-day rolling window.

Compares model predictions against actual conditions to weight
more reliable models higher in the blending engine.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "model_history.json")


def load_accuracy_weights() -> Dict[str, float]:
    """Load model accuracy weights from historical tracking.

    Returns equal weights if no history exists yet.
    """
    if not os.path.exists(HISTORY_FILE):
        return {"GFS": 1.0, "ECMWF": 1.0, "ICON": 1.0}

    try:
        with open(HISTORY_FILE) as f:
            history = json.load(f)
        accuracy = history.get("accuracy", {})
        if not accuracy:
            return {"GFS": 1.0, "ECMWF": 1.0, "ICON": 1.0}

        # Convert accuracy scores to weights (higher accuracy = higher weight)
        weights = {}
        for model, score in accuracy.items():
            weights[model] = max(0.1, score)
        return weights
    except (json.JSONDecodeError, KeyError):
        return {"GFS": 1.0, "ECMWF": 1.0, "ICON": 1.0}


def record_prediction(model_data: Dict, history_file: str = HISTORY_FILE):
    """Record current model predictions for later accuracy comparison."""
    os.makedirs(os.path.dirname(history_file), exist_ok=True)

    history = {"runs": [], "accuracy": {}}
    if os.path.exists(history_file):
        try:
            with open(history_file) as f:
                history = json.load(f)
        except json.JSONDecodeError:
            pass

    run = {
        "timestamp": datetime.now().isoformat(),
        "predictions": {},
    }

    for model_name, data in model_data.items():
        if data and "daily" in data:
            daily = data["daily"]
            run["predictions"][model_name] = {
                "temp_max": daily.get("temperature_2m_max", [None])[0],
                "temp_min": daily.get("temperature_2m_min", [None])[0],
                "snowfall": daily.get("snowfall_sum", [None])[0],
            }

    history["runs"].append(run)

    # Prune to 30 days
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    history["runs"] = [r for r in history["runs"] if r.get("timestamp", "") > cutoff]

    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)
