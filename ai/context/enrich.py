import json
import sys
from pathlib import Path

from ai.knowledge.knowledge_loader import load_service_capabilities


def extract_action(change: dict) -> str:
    """
    Determine Terraform action: create / update / delete
    """
    actions = change.get("actions", [])
    if "create" in actions:
        return "create"
    if "update" in actions:
        return "update"
    if "delete" in actions:
        return "delete"
    return "unknown"


def enrich_plan(plan_file: str, output_file: str):
    with open(plan_file, "r") as f:
        plan = json.load(f)

    service_capabilities = load_service_capabilities()

    resource_changes = plan.get("resource_changes", [])

    enriched_resources = []
    summary = {"create": 0, "update": 0, "delete": 0}

    for rc in resource_changes:
        resource_type = rc.get("type")
        change = rc.get("change", {})
        action = extract_action(change)

        if action in summary:
            summary[action] += 1

        # 🔑 CORE CHANGE — PATTERN MAPPING
        patterns = service_capabilities.get(
            resource_type,
            ["unknown_service"]
        )

        enriched_resources.append({
            "type": resource_type,
            "name": rc.get("name"),
            "action": action,
            "patterns": patterns
        })

    enriched_context = {
        "environment": "dev",  # later comes from workflow input
        "summary": summary,
        "resources": enriched_resources
    }

    with open(output_file, "w") as f:
        json.dump(enriched_context, f, indent=2)

    print("SUCCESS: Terraform plan enriched with risk patterns")
    print(json.dumps(enriched_context, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python enrich.py <tfplan.json> <enriched_context.json>")
        sys.exit(1)

    enrich_plan(sys.argv[1], sys.argv[2])
