import json
import sys
from pathlib import Path
import yaml

from ai.reasoning.llm_enrichment import enrich_with_llm


# -------------------------------------------------
# Config Loader
# -------------------------------------------------

def load_repo_config():
    cfg = Path(".ai-reviewer.yaml")
    if not cfg.exists():
        return {"environment": "dev"}

    with open(cfg) as f:
        return yaml.safe_load(f)


# -------------------------------------------------
# Core Risk Engine (DETERMINISTIC)
# -------------------------------------------------

def assess_risk(ctx: dict) -> dict:
    caps = ctx.get("capabilities_detected", {})
    summary = ctx.get("summary", {})

    is_create_only = (
        summary.get("create", 0) > 0 and
        summary.get("update", 0) == 0 and
        summary.get("delete", 0) == 0
    )

    # -------------------------------------------------
    # 🔴 HARD BLOCK — Public Data Plane
    # -------------------------------------------------
    if caps.get("data_plane") and caps.get("public_exposure"):
        return {
            "risk_level": "HIGH",
            "decision": "BLOCK",
            "confidence": 0.95,
            "reasons": [
                "Public data plane exposure detected"
            ],
            "recommendations": [
                "Disable public access to data services",
                "Use private endpoints",
                "Restrict network access",
                "Require security approval"
            ]
        }

    # -------------------------------------------------
    # 🟠 WARN — Active Infra (Compute / Control)
    # -------------------------------------------------
    if is_create_only and (
        caps.get("compute_plane") or
        caps.get("control_plane")
    ):
        return {
            "risk_level": "MEDIUM",
            "decision": "WARN",
            "confidence": 0.85,
            "reasons": [
                "Active infrastructure introduced requiring human review"
            ],
            "recommendations": [
                "Ensure security hardening standards are followed",
                "Confirm this change is intended for the environment"
            ]
        }

    # -------------------------------------------------
    # 🟢 PASS — Scaffold / Network Only
    # -------------------------------------------------
    return {
        "risk_level": "LOW",
        "decision": "PASS",
        "confidence": 0.6,
        "reasons": [
            "Create-only scaffold infrastructure without public exposure"
        ],
        "recommendations": [
            "LGTM from an infrastructure safety perspective."
        ]
    }


# -------------------------------------------------
# Entry Point
# -------------------------------------------------

def main(input_file: str, output_file: str):
    with open(input_file) as f:
        ctx = json.load(f)

    config = load_repo_config()
    env = config.get("environment", "dev")

    review = assess_risk(ctx)
    review["environment"] = env

    # -------------------------------------------------
    # 🤖 LLM ALWAYS ENABLED (EXPLAINS ONLY)
    # -------------------------------------------------
    review = enrich_with_llm(ctx, review)

    with open(output_file, "w") as f:
        json.dump(review, f, indent=2)

    print("SUCCESS: Terraform AI review generated")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python review.py <enriched_context.json> <ai_review.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
