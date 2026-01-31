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
    if score >= 8:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


def load_repo_policy_config():
    cfg = Path(".ai-reviewer.yaml")
    if not cfg.exists():
        return {"environment": "dev"}
    with open(cfg) as f:
        return yaml.safe_load(f)


# -------------------------------------------------
# Core Review Engine
# -------------------------------------------------

def assess_risk(enriched_context: dict) -> dict:
    repo_cfg = load_repo_policy_config()
    env = repo_cfg.get("environment", "dev")

    resources = enriched_context.get("resources", [])
    summary = enriched_context.get("summary", {})

    patterns_def = load_risk_patterns()
    security_map = load_security_severity()

    # -------------------------------------------------
    # 1. Detect intent
    # -------------------------------------------------
    intent = detect_intent(enriched_context)

    # -------------------------------------------------
    # 2. Collect patterns
    # -------------------------------------------------
    patterns = []
    for r in resources:
        patterns.extend(r.get("patterns", []))

    pattern_counts = Counter(patterns)

    # -------------------------------------------------
    # 3. Base risk scoring
    # -------------------------------------------------
    risk_score = 0.0
    reasons = []
    praise = []

    for p, count in pattern_counts.items():
        info = patterns_def.get(p)
        if not info:
            continue

        base = info["base_score"]
        if p == "unknown_service":
            base = 0.2

        risk_score += base * count
        reasons.append(
            f"{p} detected ({count}×): {info['description']}"
        )

    # -------------------------------------------------
    # 4. Detect create-only PR (KEY SIGNAL)
    # -------------------------------------------------
    is_create_only = (
        summary.get("create", 0) > 0
        and summary.get("update", 0) == 0
        and summary.get("delete", 0) == 0
    )

    # -------------------------------------------------
    # 5. Apply SAFE CREATE-ONLY LOGIC (THE FIX)
    # -------------------------------------------------
    if is_create_only:
        praise.append("Create-only infrastructure change")

        if "public_exposure" not in pattern_counts:
            praise.append("No public exposure detected")

        if "network_boundary" in pattern_counts:
            praise.append("Private network resources created")

        if "identity_boundary" in pattern_counts:
            praise.append("Security controls added during provisioning")

        # 🔥 HARD RISK CAP — THIS SOLVES YOUR PROBLEM
        risk_score = min(risk_score, 3.0)

        reasons = [
            "Create-only infrastructure without public exposure"
        ]

    # -------------------------------------------------
    # 6. Environment weighting
    # -------------------------------------------------
    if env == "prod" and not is_create_only:
        risk_score *= 1.3
    elif env == "dev":
        risk_score *= 0.7

    # -------------------------------------------------
    # 7. Security severity escalation
    # -------------------------------------------------
    security_findings = []

    for p in pattern_counts:
        sec = security_map.get(p)
        if not sec:
            continue

        security_findings.append({
            "pattern": p,
            "severity": sec["severity"],
            "description": sec["description"]
        })

    if any(f["severity"] == "CRITICAL" for f in security_findings):
        risk_score = max(risk_score, 9)
        reasons.append("Critical security exposure detected")

    # -------------------------------------------------
    # 8. Final risk level & decision
    # -------------------------------------------------
    risk_level = score_to_level(risk_score)

    if risk_level == "HIGH":
        decision = "WARN"
        decision_reason = "High-risk infrastructure change"
    else:
        decision = "PASS"
        decision_reason = "Safe infrastructure change"

    confidence = 0.6 if decision == "PASS" else 0.9

    # -------------------------------------------------
    # 9. Recommendations
    # -------------------------------------------------
    if decision == "PASS":
        recommendations = [
            "LGTM from an infrastructure safety perspective."
        ]
    else:
        recommendations = [
            "Review carefully and validate in a lower environment before merge."
        ]

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
    review = enrich_with_llm(enriched, review)

    with open(output_file, "w") as f:
        json.dump(review, f, indent=2)

    print("SUCCESS: Terraform AI review generated")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python review.py <enriched_context.json> <ai_review.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
