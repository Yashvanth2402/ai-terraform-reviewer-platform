import json
from pathlib import Path

BASE_PATH = Path(__file__).parent


def load_policy_packs():
    with open(BASE_PATH / "policy_packs.json", "r") as f:
        return json.load(f)
