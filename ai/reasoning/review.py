import json
import sys
from collections import Counter

from ai.knowledge.knowledge_loader import (
    load_risk_patterns,
    load_security_severity
)
from ai.reasoning.intent_detector import detect_intent
from ai.reasoning.llm_enrichment import enrich_with_llm
from ai.memory.memory_store import find_similar_prs


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def score_to_level(score: float) -> str:
    if score >= 8:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


# -------------------------------------------------
# Core Pattern-Based Risk Engine
# -------------------------------------------------

def assess_risk(enriched_context: dict) -> dict:
    env = enriched_context.get("environment", "dev")
    resources = enriched_context.get("resources", [])
    summary = enriched_context.get("summary", {})

    risk_patterns = load_risk_patterns()
    security_severity_map = load_security_severity()

    # -------------------------------------------------
    # 1. Detect intent (WHY the PR exists)
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
    # 3. Base risk score from patterns
    # -------------------------------------------------
    risk_score = 0.0
    reasons = []
    praise = []

    for pattern, count in pattern_counts.items():
        info = risk_patterns.get(pattern)
        if not info:
            continue

        contribution = info["base_score"] * count
        risk_score += contribution

        reasons.append(
            f"{pattern} detected ({count}×): {info['description']}"
        )

    # -------------------------------------------------
    # 4. Risk reducers (GOOD engineering signals)
    # -------------------------------------------------
    if summary.get("update", 0) == 0 and summary.get("delete", 0) == 0:
        risk_score -= 2
        praise.append("Create-only change (no destructive actions)")

    if "public_exposure" not in pattern_counts:
        risk_score -= 2
        praise.append("No public exposure detected")

    if intent == "bootstrap":
        risk_score -= 1
        praise.append("Bootstrap-style infrastructure setup")

    if intent == "security_hardening":
        risk_score -= 2
        praise.append("Security hardening change detected")

    # -------------------------------------------------
    # 5. Intent-based escalation
    # -------------------------------------------------
    if intent == "risky_change":
        risk_score += 2
        reasons.append("High-impact or destructive intent detected")

    # -------------------------------------------------
    # 6. Environment weighting
    # -------------------------------------------------
    if env == "prod":
        risk_score *= 1.3
    elif env == "dev":
        risk_score *= 0.7

    # -------------------------------------------------
    # 7. Security Severity Engine
    # -------------------------------------------------
    security_findings = []

    for pattern in pattern_counts:
        sec_info = security_severity_map.get(pattern)
        if not sec_info:
            continue

        severity = sec_info["severity"]

        # Environment-aware downgrade
        if env == "dev" and severity == "HIGH":
            severity = "MEDIUM"

        security_findings.append({
            "pattern": pattern,
            "severity": severity,
            "description": sec_info["description"]
        })

    # Security-based escalation
    if any(f["severity"] == "CRITICAL" for f in security_findings):
        risk_score += 4
        reasons.append("Critical security exposure detected")

    elif any(f["severity"] == "HIGH" for f in security_findings) and env == "prod":
        risk_score += 2
        reasons.append("High security exposure in production")

    # -------------------------------------------------
    # 8. Historical context (learning, not guessing)
    # -------------------------------------------------
    resource_types = [r["type"] for r in resources]
    history = find_similar_prs(resource_types, env)

    if history:
        risk_score += 1
        reasons.append(
            f"Historical context: {len(history)} similar change(s) observed previously"
        )

    # -------------------------------------------------
    # 9. Final risk & confidence
    # -------------------------------------------------
    risk_level = score_to_level(risk_score)
    confidence = min(0.95, max(0.45, 0.5 + (risk_score / 10)))

    # -------------------------------------------------
    # 10. Recommendations (senior engineer tone)
    # -------------------------------------------------
    recommendations = []

    if risk_level == "LOW":
        recommendations.append(
            "LGTM from an infrastructure safety perspective."
        )

    elif risk_level == "MEDIUM":
        recommendations.append(
            "Validate this change in a lower environment before promotion."
        )

    else:
        recommendations.extend([
            "Run this change during a defined maintenance window.",
            "Ensure a rollback plan is documented and tested.",
            "Notify dependent teams if shared infrastructure is involved."
        ])

    # -------------------------------------------------
    # 11. Build final review object
    # -------------------------------------------------
    review = {
        "environment": env,
        "intent": intent,
        "risk_level": risk_level,
        "confidence": round(confidence, 2),
        "reasons": list(dict.fromkeys(reasons)),
        "praise": praise,
        "security_findings": security_findings,
        "review_comments": [],
        "recommendations": recommendations
    }

    return review


# -------------------------------------------------
# Entry Point
# -------------------------------------------------

def main(input_file: str, output_file: str):
    with open(input_file, "r") as f:
        enriched_context = json.load(f)

    review = assess_risk(enriched_context)

    # LLM is used ONLY to explain, never to decide
    review = enrich_with_llm(enriched_context, review)

    with open(output_file, "w") as f:
        json.dump(review, f, indent=2)

    print("SUCCESS: Production-grade AI Terraform review generated")
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python review.py <enriched_context.json> <ai_review.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
