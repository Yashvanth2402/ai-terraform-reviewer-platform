import json
import sys
from collections import defaultdict


def enrich_plan(plan_path: str, output_path: str):
    summary = defaultdict(int)
    resources = []
    global_patterns = set()

    try:
        with open(plan_path, "r") as f:
            plan = json.load(f)
    except Exception as e:
        # HARD FAIL SAFE: still write output
        enriched = {
            "resources": [],
            "summary": {},
            "error": f"Failed to read plan: {str(e)}"
        }
        with open(output_path, "w") as out:
            json.dump(enriched, out, indent=2)
        print("WARN: Failed to parse tfplan.json, wrote empty enriched context")
        return

    # -----------------------------------------
    # Resource-level detection
    # -----------------------------------------
    for rc in plan.get("resource_changes", []):
        rtype = rc.get("type", "unknown")
        name = rc.get("name", "unknown")
        actions = rc.get("change", {}).get("actions", [])

        for a in actions:
            summary[a] += 1

        patterns = set()

        if rtype.startswith("azurerm_virtual_network") or rtype.startswith("azurerm_subnet"):
            patterns.add("network_boundary")

        if rtype.startswith("azurerm_network_security_group"):
            patterns.add("identity_boundary")

        if rtype.startswith("azurerm_resource_group"):
            patterns.add("blast_radius")

        if rtype == "tls_private_key":
            patterns.add("secret_material")

        if rtype in (
            "azurerm_linux_virtual_machine",
            "azurerm_windows_virtual_machine",
        ):
            patterns.add("compute_provisioning")

        resources.append({
            "type": rtype,
            "name": name,
            "actions": actions,
            "patterns": list(patterns)
        })

        global_patterns.update(patterns)

    # -----------------------------------------
    # Output-level detection (SAFE)
    # -----------------------------------------
    outputs = (
        plan.get("planned_values", {})
            .get("outputs", {})
    )

    for _, output in outputs.items():
        if isinstance(output, dict) and output.get("sensitive", False):
            global_patterns.add("secret_exposure")

    # Attach global patterns to each resource
    for r in resources:
        for p in global_patterns:
            if p not in r["patterns"]:
                r["patterns"].append(p)

    enriched = {
        "resources": resources,
        "summary": dict(summary)
    }

    # 🔒 GUARANTEED WRITE
    with open(output_path, "w") as out:
        json.dump(enriched, out, indent=2)

    print(f"SUCCESS: Enriched context written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python enrich.py <tfplan.json> <enriched_context.json>")
        sys.exit(1)

    enrich_plan(sys.argv[1], sys.argv[2])
