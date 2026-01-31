import json
import sys
from collections import Counter
from pathlib import Path
import yaml

from ai.knowledge.knowledge_loader import (
    load_risk_patterns,
    load_security_severity,
)
from ai.reasoning.intent_detector import detect_intent
from ai.reasoning.llm_enrichment import enrich_with_llm


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def score_to_level(score: float) -> str:
    if score >= 7:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


def load_repo_config():
    cfg = Path(".ai-reviewer.yaml")
    if not cfg.exists():
        return {"environment": "dev"}
    with open(cfg) as f:
        return yaml.safe_load(f)


# -------------------------------------------------
# Core Review Engine
# -------------------------------------------------

def assess_risk(enriched_context: dict) -> dict:
    repo_cfg = load_repo_config()
    env = repo_cfg.get("environment", "dev")

    resources = enriched_context.get("resources", [])
    summary = enriched_context.get("summary", {})

    risk_defs = load_risk_patterns()
    security_defs = load_security_severity()

    # -------------------------------------------------
    # 1. Detect intent
    # -------------------------------------------------
    intent = detect_intent(enriched_context)

    # -------------------------------------------------
    # 2. Collect patterns
    # -------------------------------------------------
    all_patterns = []
    for r in resources:
        all_patterns.extend(r.get("patterns", []))

    pattern_counts = Counter(all_patterns)

    # -------------------------------------------------
    # 3. Base risk score
    # -------------------------------------------------
    risk_score = 0.0

    for pattern, count in pattern_counts.items():
        info = risk_defs.get(pattern)
        if not info:
            continue

        base = info["base_score"]
        if pattern == "unknown_service":
            base = 0.2

        risk_score += base * count

    # -------------------------------------------------
    # 4. Detect create-only PR
    # -------------------------------------------------
    is_create_only = (
        summary.get("create", 0) > 0
        and summary.get("update", 0) == 0
        and summary.get("delete", 0) == 0
    )

    has_compute = "compute_provisioning" in pattern_counts
    has_secrets = any(
        p in pattern_counts
        for p in ["secret_material", "secret_exposure"]
    )

    scaffold_only = is_create_only and not has_compute and not has_secrets
    active_create = is_create_only and (has_compute or has_secrets)

    reasons = []
    praise = []

    # -------------------------------------------------
    # 5. Scaffold-only infra (SAFE)
    # -------------------------------------------------
    if scaffold_only:
        risk_score = min(risk_score, 2.0)
        reasons = [
            "Create-only scaffold infrastructure without public exposure"
        ]
        praise.extend([
            "No compute resources provisioned",
            "No secrets generated or exposed",
            "Safe for development iteration"
        ])

    # -------------------------------------------------
    # 6. Active create infra (REAL-WORLD RULE)
    # -------------------------------------------------
    if active_create:
        risk_score = max(risk_score, 4.0)
        reasons = [
            "Active infrastructure created requiring human review"
        ]

        if has_secrets:
            reasons.append(
                "Secret material generated or exposed in Terraform"
            )

        if has_compute:
            reasons.append(
                "Compute resources provisioned requiring security hardening"
            )

    # -------------------------------------------------
    # 7. Security severity escalation
    # -------------------------------------------------
    security_findings = []

    for p in pattern_counts:
        sec = security_defs.get(p)
        if not sec:
            continue

        security_findings.append({
            "pattern": p,
            "severity": sec["severity"],
            "description": sec["description"]
        })

        if sec["severity"] == "CRITICAL":
            risk_score = max(risk_score, 8)

    # -------------------------------------------------
    # 8. Environment weighting
    # -------------------------------------------------
    if env == "prod":
        risk_score *= 1.2
    else:
        risk_score *= 0.9

    # -------------------------------------------------
    # 9. Risk level calculation
    # -------------------------------------------------
    risk_level = score_to_level(risk_score)

    # -------------------------------------------------
    # 🔒 FINAL RISK FLOOR (LAST FIX)
    # -------------------------------------------------
    # Active infrastructure must NEVER be LOW risk
    if active_create and risk_level == "LOW":
        risk_level = "MEDIUM"

    # -------------------------------------------------
    # 10. Final decision
    # -------------------------------------------------
    if scaffold_only:
        decision = "PASS"
        decision_reason = "Safe scaffold infrastructure change"
        confidence = 0.6
        recommendations = [
            "LGTM from an infrastructure safety perspective."
        ]

    elif active_create:
        decision = "WARN"
        decision_reason = "Active infrastructure requires human approval"
        confidence = 0.85
        recommendations = [
            "Avoid generating or storing secrets in Terraform.",
            "Use Azure Key Vault or pre-generated credentials.",
            "Ensure compute resources follow security hardening standards.",
            "Require human review before merge."
        ]

    elif risk_level == "MEDIUM":
        decision = "WARN"
        decision_reason = "Infrastructure change requires review"
        confidence = 0.75
        recommendations = [
            "Review carefully and validate in a lower environment."
        ]

    else:
        decision = "BLOCK"
        decision_reason = "High-risk infrastructure change"
        confidence = 0.9
        recommendations = [
            "Do not merge until security risks are addressed."
        ]

    # -------------------------------------------------
    # 11. Final review object
    # -------------------------------------------------
    return {
        "environment": env,
        "intent": intent,
        "risk_level": risk_level,
        "confidence": confidence,
        "decision": decision,
        "decision_reason": decision_reason,
        "reasons": reasons,
        "praise": praise,
        "security_findings": security_findings,
        "recommendations": recommendations,
    }


# -------------------------------------------------
# Entry Point
# -------------------------------------------------

def main(input_file: str, output_file: str):
    with open(input_file) as f:
        enriched = json.load(f)

    review = assess_risk(enriched)

    # LLM explains only — never decides
    review = enrich_with_llm(enriched, review)

    with open(output_file, "w") as f:
        json.dump(review, f, indent=2)

    print("SUCCESS: Terraform AI review generated")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python review.py <enriched_context.json> <ai_review.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
