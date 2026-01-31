import json
import sys
from collections import Counter

from ai.reasoning.llm_enrichment import enrich_with_llm
from ai.memory.memory_store import find_similar_prs


# -------------------------------------------------
# Helper functions
# -------------------------------------------------

def has_resource(resources, rtype):
    return any(r["type"] == rtype for r in resources)


def count_resources(resources, rtype):
    return sum(1 for r in resources if r["type"] == rtype)


def only_creates(summary):
    return summary.get("update", 0) == 0 and summary.get("delete", 0) == 0


# -------------------------------------------------
# Core Risk Engine
# -------------------------------------------------

def assess_risk(enriched_context: dict) -> dict:
    env = enriched_context.get("environment", "unknown")
    resources = enriched_context.get("resources", [])
    summary = enriched_context.get("summary", {})

    resource_types = [r["type"] for r in resources]
    type_counts = Counter(resource_types)

    risk = "LOW"
    confidence = 0.3
    reasons = []
    comments = []
    recommendations = []

    # =================================================
    # 🔥 HARD DANGER (ALWAYS HIGH)
    # =================================================

    if has_resource(resources, "azurerm_public_ip"):
        risk = "HIGH"
        confidence = 0.9
        reasons.append("Public IP resource detected, increasing exposure risk.")
        comments.append("🚨 Public IP detected. Ensure this is strictly required and protected.")
        recommendations.append("Avoid public IPs unless absolutely necessary. Prefer private endpoints.")

    if has_resource(resources, "azurerm_network_security_group"):
        for r in resources:
            if r["type"] == "azurerm_network_security_group":
                for rule in r.get("security_rules", []):
                    if rule.get("source_address_prefix") == "*" and rule.get("destination_port_range") == "22":
                        reasons.append("SSH (22) is open to all sources.")
                        comments.append("⚠️ SSH open to the internet. Restrict source IPs.")
                        recommendations.append("Limit SSH access to corporate IP ranges or use Bastion.")

    # =================================================
    # 🌐 NETWORKING (CONTEXT-AWARE)
    # =================================================

    network_resources = {
        "azurerm_virtual_network",
        "azurerm_subnet",
        "azurerm_route_table",
        "azurerm_nat_gateway"
    }

    network_changes = any(t in network_resources for t in resource_types)

    if network_changes:
        reasons.append("Azure networking resources are being modified.")

        if not only_creates(summary):
            risk = "HIGH"
            confidence = max(confidence, 0.85)
            comments.append("🚨 Network modification detected (update/delete). Rollback can be complex.")
            recommendations.append("Validate routing, CIDR overlaps, and rollback strategy.")
        else:
            risk = max(risk, "MEDIUM", key=["LOW", "MEDIUM", "HIGH"].index)
            confidence = max(confidence, 0.6)
            comments.append("⚠️ New networking components added. Review CIDR and dependencies.")

    # =================================================
    # 🖥️ COMPUTE (SAFE VS UNSAFE)
    # =================================================

    if has_resource(resources, "azurerm_linux_virtual_machine"):
        if env == "prod":
            risk = "HIGH"
            confidence = max(confidence, 0.85)
            reasons.append("Compute resources introduced in production.")
            comments.append("🚨 VM changes in production detected.")
            recommendations.append("Use phased rollout or blue-green strategy.")
        else:
            reasons.append("VM resources introduced in non-production.")
            comments.append("ℹ️ VM changes in non-prod environment.")

    # =================================================
    # 🧱 SAFE PATTERNS (RISK REDUCERS)
    # =================================================

    safe_signals = []

    if only_creates(summary):
        safe_signals.append("Create-only changes (no destructive actions).")

    if not has_resource(resources, "azurerm_public_ip"):
        safe_signals.append("No public IP exposure.")

    if has_resource(resources, "azurerm_network_security_group"):
        safe_signals.append("Explicit network security group defined.")

    if has_resource(resources, "azurerm_linux_virtual_machine"):
        for r in resources:
            if r["type"] == "azurerm_linux_virtual_machine" and r.get("count", 1) == 0:
                safe_signals.append("VM explicitly disabled in CI/PR context.")

    if len(safe_signals) >= 3 and risk != "HIGH":
        risk = "LOW"
        confidence = 0.7
        comments.append("✅ Safe infrastructure patterns detected.")
        reasons.extend(safe_signals)

    # =================================================
    # 📦 CHANGE VOLUME
    # =================================================

    total_changes = sum(summary.values())

    if total_changes >= 8:
        risk = "HIGH"
        confidence = max(confidence, 0.9)
        reasons.append("Large infrastructure change set detected.")
        comments.append("⚠️ Consider splitting this PR into smaller changes.")
        recommendations.append("Reduce blast radius by staging changes.")

    elif total_changes >= 4:
        risk = max(risk, "MEDIUM", key=["LOW", "MEDIUM", "HIGH"].index)
        confidence = max(confidence, 0.6)

    # =================================================
    # 📚 HISTORICAL MEMORY (DAY 11)
    # =================================================

    history = find_similar_prs(resource_types, env)

    if history:
        reasons.append(f"Similar patterns found in {len(history)} previous PR(s).")
        comments.append("📚 Historical context applied to this review.")

        if any(h.get("risk_level") == "HIGH" for h in history):
            confidence = min(confidence + 0.1, 0.95)

    # =================================================
    # 🧠 FINAL RECOMMENDATIONS (SMART, NOT GENERIC)
    # =================================================

    if risk == "LOW":
        recommendations.append("Proceed with standard review and merge process.")

    elif risk == "MEDIUM":
        recommendations.append("Ensure validation in lower environment before promotion.")

    elif risk == "HIGH":
        recommendations.extend([
            "Run during maintenance window.",
            "Ensure rollback plan is documented.",
            "Notify dependent teams if applicable."
        ])

    return {
        "environment": env,
        "risk_level": risk,
        "confidence": round(confidence, 2),
        "reasons": list(dict.fromkeys(reasons)),
        "review_comments": list(dict.fromkeys(comments)),
        "recommendations": list(dict.fromkeys(recommendations))
    }


# -------------------------------------------------
# Entry Point
# -------------------------------------------------

def main(input_file, output_file):
    with open(input_file, "r") as f:
        enriched_context = json.load(f)

    review = assess_risk(enriched_context)
    review = enrich_with_llm(enriched_context, review)

    with open(output_file, "w") as f:
        json.dump(review, f, indent=2)

    print("SUCCESS: Context-aware AI review generated")
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python review.py <enriched_context.json> <ai_review.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
