import json
import sys
from collections import defaultdict
from ai.knowledge.knowledge_loader import load_service_capabilities


def enrich_plan(plan_file: str, output_file: str):
    with open(plan_file) as f:
        plan = json.load(f)

    service_caps = load_service_capabilities()

    enriched = {
        "resources": [],
        "capabilities_detected": defaultdict(bool),
        "summary": {"create": 0, "update": 0, "delete": 0}
    }

    for rc in plan.get("resource_changes", []):
        rtype = rc["type"]
        action = rc["change"]["actions"][0]

        enriched["summary"][action] += 1

        caps = service_caps.get(rtype, [])

        resource_entry = {
            "type": rtype,
            "action": action,
            "capabilities": caps,
            "flags": {}
        }

        # Detect PUBLIC exposure generically
        after = rc["change"].get("after", {}) or {}
        if after.get("container_access_type") in ["blob", "container"]:
            resource_entry["flags"]["public_exposure"] = True

        if after.get("public_network_access_enabled") is True:
            resource_entry["flags"]["public_exposure"] = True

        if after.get("allow_nested_items_to_be_public") is True:
            resource_entry["flags"]["public_exposure"] = True

        for cap in caps:
            enriched["capabilities_detected"][cap] = True

        if resource_entry["flags"].get("public_exposure"):
            enriched["capabilities_detected"]["public_exposure"] = True

        enriched["resources"].append(resource_entry)

    enriched["capabilities_detected"] = dict(enriched["capabilities_detected"])

    with open(output_file, "w") as f:
        json.dump(enriched, f, indent=2)

    print(f"SUCCESS: Enriched context written to {output_file}")


if __name__ == "__main__":
    enrich_plan(sys.argv[1], sys.argv[2])
