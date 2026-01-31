import json
import sys
from collections import Counter
from pathlib import Path
import yaml

from ai.knowledge.knowledge_loader import (
    load_risk_patterns,
    load_security_severity,
    load_blocking_rules
)
from ai.reasoning.intent_detector import detect_intent
from ai.reasoning.llm_enrichment import enrich_with_llm
from ai.memory.memory_store import find_similar_prs
from ai.policies.policy_loader import load_policy_packs


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
    config_path = Path(".ai-reviewer.yaml")
    if not config_path.exists():
        return {
            "environment": "dev",
            "enabled_policies": []
        }

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# -------------------------------------------------
# Core Review Engine
# -------------------------------------------------

def assess_risk(enriched_context: dict) -> dict:
    repo_config = load_repo_policy_config()

    env = repo_config.get("environment", "dev")
    enabled_policies = repo_config.get("enabled_policies", [])

    resources = enriched_context.get("resources", [])
    summary = enriched_context.get("summary", {})

    risk_patterns = load_risk_patterns()
    security_severity_map = load_security_severity()
    policy_packs = load_policy_packs()
    blocking_rules = load_blocking_rules()

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
    # 3. Base risk scoring (LOW unknown_service impact)
    # -------------------------------------------------
    risk_score = 0.0
    reasons = []
    praise = []

    for pattern, count in pattern_counts.items():
        info = risk_patterns.get(pattern)
        if not info:
            continue

        base = info["base_score"]
        if pattern == "unknown_service":
            base = 0.2

        risk_score += base * count
        reasons.append(
            f"{pattern} detected ({count}×): {info['description']}"
        )

    # -------------------------------------------------
    # 4. Detect create-only PR (KEY SIGNAL)
    # -------------------------------------------------
    is_create_only = (
        summary.get("create", 0) > 0 and
        summary.get("update", 0) == 0 and
        summary.get("delete", 0) == 0
    )

    # -------------------------------------------------
    # 5. Create-only shared infra downgrade (CRITICAL FIX)
    # -------------------------------------------------
    if is_create_only:
        if "blast_radius" in pattern_counts:
            risk_score -= 2
            praise.append("Create-only shared infrastructure (safe pattern)")

        if "network_boundary" in pattern_counts and "public_exposure" not in pattern_counts:
            risk_score -= 2
            praise.append("Private network creation without public exposure")

        if "identity_boundary" in pattern_counts:
            risk_score -= 1.5
            praise.append("Identity controls added during initial provisioning")

    # -------------------------------------------------
    # 6. Additional risk reducers
    # -------------------------------------------------
    if "public_exposure" not in pattern_counts:
        risk_score -= 1
        praise.append("No public exposure detected")

    if intent == "bootstrap":
        risk_score -= 1
        praise.append("Bootstrap-style infrastructure setup")

    if intent == "security_hardening":
        risk_score -= 2
        praise.append("Security hardening change detected")

    # -------------------------------------------------
    # 7. Intent escalation (ONLY destructive intent)
    # -------------------------------------------------
    if intent == "risky_change" and summary.get("delete", 0) > 0:
        risk_score += 2
        reasons.append("Destructive infrastructure change detected")

    # -------------------------------------------------
    # 8. Environment weighting
    # -------------------------------------------------
    if env == "prod":
        risk_score *= 1.3
    elif env == "dev":
        risk_score *= 0.7

    # -------------------------------------------------
    # 9. Security severity engine
    # -------------------------------------------------
    security_findings = []

    for pattern in pattern_counts:
        sec = security_severity_map.get(pattern)
        if not sec:
            continue

        severity = sec["severity"]
        if env == "dev" and severity == "HIGH":
            severity = "MEDIUM"

        security_findings.append({
            "pattern": pattern,
            "severity": severity,
            "description": sec["description"]
        })

    if any(f["severity"] == "CRITICAL" for f in security_findings):
        risk_score += 4
        reasons.append("Critical security exposure detected")

    # -------------------------------------------------
    # 10. Context-aware policy evaluation (FIXED)
    # -------------------------------------------------
    raw_policy_hits = []

    for policy_name in enabled_policies:
        policy = policy_packs.get(policy_name)
        if not policy:
            continue

        for pattern in policy["patterns"]:
            if pattern in pattern_counts:
                raw_policy_hits.append({
                    "policy": policy_name,
                    "pattern": pattern,
                    "description": policy["description"]
                })

    policy_violations = []

    for v in raw_policy_hits:
        if is_create_only and v["pattern"] in ["network_boundary", "identity_boundary"]:
            continue
        policy_violations.append(v)

    if policy_violations:
        risk_score += len(policy_violations)
        reasons.append(
            f"Policy violations detected: {', '.join(p['policy'] for p in policy_violations)}"
        )

    # -------------------------------------------------
    # 11. Historical context (light weight)
    # -------------------------------------------------
    resource_types = [r["type"] for r in resources]
    history = find_similar_prs(resource_types, env)

    if history and risk_score >= 4:
        risk_score += 1
        reasons.append(
            f"Historical context: {len(history)} similar risky changes observed"
        )

    # -------------------------------------------------
    # 12. Final risk & confidence
    # -------------------------------------------------
    risk_level = score_to_level(risk_score)
    confidence = min(0.95, max(0.45, 0.55 + (risk_score / 12)))

    # -------------------------------------------------
    # 13. Decision Engine
    # -------------------------------------------------
    decision = "PASS"
    decision_reason = "Safe infrastructure change"

    if any(f["severity"] == "CRITICAL" for f in security_findings):
        decision = "BLOCK"
        decision_reason = "Critical security issue detected"

    elif env == "prod" and risk_level == "HIGH":
        decision = "BLOCK"
        decision_reason = "High-risk change in production"

    elif policy_violations or risk_level == "MEDIUM":
        decision = "WARN"
        decision_reason = "Review recommended due to moderate risk"

    # -------------------------------------------------
    # 14. Recommendations
    # -------------------------------------------------
    recommendations = []

    if decision == "PASS":
        recommendations.append("LGTM from an infrastructure safety perspective.")

    elif decision == "WARN":
        recommendations.append(
            "Review carefully and validate in a lower environment before merge."
        )

    else:
        recommendations.extend([
            "Run this change during a defined maintenance window.",
            "Ensure a rollback plan is documented and tested.",
            "Notify dependent teams if shared infrastructure is involved."
        ])

    # -------------------------------------------------
    # 15. Final review object
    # -------------------------------------------------
    return {
        "environment": env,
        "intent": intent,
        "risk_level": risk_level,
        "confidence": round(confidence, 2),
        "decision": decision,
        "decision_reason": decision_reason,
        "reasons": list(dict.fromkeys(reasons)),
        "praise": praise,
        "security_findings": security_findings,
        "policy_violations": policy_violations,
        "review_comments": [],
        "recommendations": recommendations
    }


# -------------------------------------------------
# Entry Point
# -------------------------------------------------

def main(input_file: str, output_file: str):
    with open(input_file, "r") as f:
        enriched_context = json.load(f)

    review = assess_risk(enriched_context)

    # LLM explanation (optional)
    review = enrich_with_llm(enriched_context, review)

    with open(output_file, "w") as f:
        json.dump(review, f, indent=2)

    print("SUCCESS: Context-aware AI Terraform review generated")
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python review.py <enriched_context.json> <ai_review.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
