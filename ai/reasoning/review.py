import json
import sys

from ai.reasoning.llm_enrichment import enrich_with_llm
from ai.memory.memory_store import find_similar_prs


def assess_risk(enriched_context: dict) -> dict:
    environment = enriched_context.get("environment", "unknown")
    resources = enriched_context.get("resources", [])
    summary = enriched_context.get("summary", {})

    risk = "LOW"
    reasons = []
    comments = []
    recommendations = []

    # -------------------------------------------------
    # Signal 1: Shared Infrastructure (Blast Radius)
    # -------------------------------------------------
    shared_changes = [
        r for r in resources if r.get("classification") == "shared-infra"
    ]
    if shared_changes:
        risk = "MEDIUM"
        reasons.append(
            "Shared Azure infrastructure is being modified, increasing blast radius across workloads."
        )
        comments.append(
            "⚠️ Shared Azure infrastructure change detected. "
            "Failures here can impact multiple teams and services."
        )

    # -------------------------------------------------
    # Signal 2: Azure Networking Risk
    # -------------------------------------------------
    network_types = ["azurerm_virtual_network", "azurerm_subnet"]
    network_changes = [
        r for r in resources if r.get("type") in network_types
    ]
    if network_changes:
        risk = "HIGH"
        reasons.append(
            "Azure networking resources are being modified, which can affect connectivity, routing, or IP allocation."
        )
        comments.append(
            "🚨 Azure network-level changes detected. "
            "Subnet or VNet changes are high risk and difficult to rollback."
        )

    # -------------------------------------------------
    # Signal 3: Environment Escalation
    # -------------------------------------------------
    if environment == "prod":
        risk = "HIGH"
        reasons.append(
            "Changes are targeting the production environment with potential customer impact."
        )
        comments.append(
            "🚨 Production environment change detected. "
            "Recommend maintenance window, validation plan, and rollback strategy."
        )

    # -------------------------------------------------
    # Signal 4: Change Volume
    # -------------------------------------------------
    total_changes = (
        summary.get("create", 0)
        + summary.get("update", 0)
        + summary.get("delete", 0)
    )
    if total_changes >= 5:
        risk = "HIGH"
        reasons.append(
            "Multiple infrastructure changes in a single deployment increase operational risk."
        )
        comments.append(
            "⚠️ Large infrastructure change detected. "
            "Consider breaking this into smaller, staged deployments."
        )

    # -------------------------------------------------
    # Confidence Scoring (Base)
    # -------------------------------------------------
    confidence = 0.3
    if risk == "MEDIUM":
        confidence = 0.6
    elif risk == "HIGH":
        confidence = 0.85

    # -------------------------------------------------
    # Actionable Recommendations
    # -------------------------------------------------
    if risk == "HIGH":
        recommendations.extend([
            "Run this change during a defined maintenance window.",
            "Ensure a rollback plan is documented and tested.",
            "Validate impact in a lower environment before production rollout."
        ])

    if any(r.get("type") == "azurerm_subnet" for r in resources):
        recommendations.append(
            "Verify subnet CIDR usage to avoid IP exhaustion or overlapping address ranges."
        )

    # -------------------------------------------------
    # Day 11 — Historical PR Memory Signal
    # -------------------------------------------------
    resource_types = [r.get("type") for r in resources]

    historical_prs = find_similar_prs(resource_types, environment)

    if historical_prs:
        reasons.append(
            f"Similar infrastructure changes were detected in {len(historical_prs)} previous PR(s)."
        )
        comments.append(
            "📚 Historical context: Similar changes have occurred before. "
            "Review past outcomes to avoid repeating issues."
        )

        # Escalate confidence if repeated high-risk history
        high_risk_history = [
            pr for pr in historical_prs if pr.get("risk_level") == "HIGH"
        ]
        if high_risk_history and risk != "LOW":
            confidence = min(confidence + 0.1, 0.95)

    return {
        "environment": environment,
        "risk_level": risk,
        "confidence": confidence,
        "reasons": reasons,
        "review_comments": comments,
        "recommendations": recommendations
    }


def main(input_file: str, output_file: str):
    # Load enriched Terraform context
    with open(input_file, "r") as f:
        enriched_context = json.load(f)

    # -----------------------------
    # Deterministic AI Reasoning
    # -----------------------------
    review = assess_risk(enriched_context)

    # -----------------------------
    # LLM Enrichment (Explanation Only)
    # -----------------------------
    review = enrich_with_llm(enriched_context, review)

    # Write final AI review output
    with open(output_file, "w") as f:
        json.dump(review, f, indent=2)

    print("SUCCESS: AI review generated with history-aware reasoning and LLM explanation")
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python review.py <enriched_context.json> <ai_review.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
