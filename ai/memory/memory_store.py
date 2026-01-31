import json
import os
from datetime import datetime

MEMORY_FILE = "ai/memory/pr_memory.json"


def load_memory() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return {"prs": []}

    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def save_memory(memory: dict):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def record_pr(pr_number: int, review: dict, outcome: str = "unknown"):
    """
    Append PR review outcome to memory.
    """
    memory = load_memory()

    entry = {
        "pr_number": pr_number,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": review.get("environment"),
        "risk_level": review.get("risk_level"),
        "confidence": review.get("confidence"),
        "resources_changed": list(
            {r.get("type") for r in review.get("resources", [])}
            if review.get("resources")
            else []
        ),
        "outcome": outcome
    }

    memory["prs"].append(entry)
    save_memory(memory)


def find_similar_prs(resources: list, environment: str) -> list:
    """
    Find past PRs touching similar resources in same environment.
    """
    memory = load_memory()
    matches = []

    for pr in memory.get("prs", []):
        if pr["environment"] != environment:
            continue

        if any(res in pr["resources_changed"] for res in resources):
            matches.append(pr)

    return matches
