import json
from pathlib import Path


BASE_PATH = Path(__file__).parent


def load_risk_patterns():
    with open(BASE_PATH / "risk_patterns.json", "r") as f:
        return json.load(f)["patterns"]


def load_service_capabilities():
    with open(BASE_PATH / "service_capabilities.json", "r") as f:
        return json.load(f)
