import json
import sys
from collections import defaultdict


def enrich_plan(plan_path: str, output_path: str):
    with open(plan_path, "r") as f:
        plan = json.load(f)

    resources = []
    summary = defaultdict(int)
    global_patterns = set()

    # -----------------------------------------
    # Resource-level detection
    # -----------------------------------------
    for rc in plan.get("resource_changes", []):
        rtype = rc["type"]
        name = rc["name"]
        actions = rc["change"]["actions"]

        for a in actions:
            summary[a] += 1

        patterns = set()

        # Core infra patterns
        if rtype.startswith("azurerm_virtual_network") or rtype.startswith("azurerm_subnet"):
            patterns.add("network_boundary")

        if rtype.startswith("azurerm_network_security_group"):
            patterns.add("identity_boundary")

        if rtype.startswith("azurerm_resource_group"):
            patterns.add("blast_radius")

        # 🔐 Secret material generation
        if rtype == "tls_private_key":
            patterns.add("secret_material")

        # 🖥️ Compute provisioning
        if rtype in [
            "azurerm_linux_virtual_machine",
            "azurerm_windows_virtual_machine"
        ]:
            patterns.add("compute_provisioning")

        resources.append({
            "type": rtype,
            "name": name,
            "actions": actions,
            "patterns": list(patterns)
        })

        global_patterns.update(patterns)

    # -----------------------------------------
    # Output-level detection (CRITICAL)
    # -----------------------------------------
    outputs = plan.get("planned_values", {}).get("outputs", {})

    for _, output in outputs.items():
        if output.get("sensitive", False):
            global_patterns.add("secret_exposure")

    # Attach global patterns to all resources
    for r in resources:
        r["patterns"].extend(
            p for p in global_patterns if p not in r["patterns"]
        )

    enriched = {
        "resources": resources,
        "summary": dict(summary)
    }

    with open(output_path, "w") as f:
        json.dump(enriched, f, indent=2)

    print(f"SUCCESS: Enriched context written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python enrich.py <tfplan.json> <enriched_context.json>")
        sys.exit(1)

    enrich_plan(sys.argv[1], sys.argv[2])
