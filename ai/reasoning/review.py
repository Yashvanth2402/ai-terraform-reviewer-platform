import json
import sys
from collections import Counter

from ai.knowledge.knowledge_loader import load_risk_patterns
from ai.reasoning.intent_detector import detect_intent
from ai.reasoning.llm_enrichment import enrich_with_llm
from ai.memory.memory_store import find_similar_prs


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def score_to_level(score: float) -> str:
    if score >= 7:
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

    # -------------------------------------------------
    # 1. Detect intent (WHY this PR exists)
    # -------------------------------------------------
    intent = detect_intent(enriched_context)

    # -------------------------------------------------
    # 2. Collect all risk patterns
    # -------------------------------------------------
    pattern_list = []
    for r in resources:
        pattern_list.extend(r.get("patterns", []))

    pattern_counts = Counter(pattern_list)

    # -------------------------------------------------
    # 3. Base risk score from patterns
    # -------------------------------------------------
    risk_score = 0.0
    reasons = []

    for pattern, count in pattern_counts.items():
        pattern_info = risk_patterns.get(pattern)
        if not pattern_info:
            continue

        contribution = pattern_info["base_score"] * count
        risk_score += contribution

        reasons.append(
            f"{pattern} detected ({count}×): {pattern_info['description']}"
        )

    # -------------------------------------------------
    # 4. Risk reducers (GOOD PR SIGNALS)
    # -------------------------------------------------
    reducers = []

    create_only = summary.get("update", 0) == 0 and summary.get("delete", 0) == 0
    if create_only:
        risk_score -= 2
        reducers.append("Create-only change (no destructive actions)")

    no_public_exposure = "public_exposure" not in pattern_counts
    if no_public_exposure:
        risk_score -= 2
        reducers.append("No public exposure detected")

    # CI-safe / gated compute (VM disabled, feature-flagged)
    gated_compute = any(
        r["type"] == "azurerm_linux_virtual_machine" and r.get("action") == "create"
        for r in resources
    )
    if gated_compute:
        risk_score -= 1
        reducers.append("Compute resources are gated / CI-safe")

    # -------------------------------------------------
    # 5. Intent-based adjustment (human reasoning)
    # -------------------------------------------------
    if intent == "bootstrap":
        risk_score -= 1
        reducers.append("Bootstrap intent detected (first-time infra setup)")

    if intent == "security_hardening":
        risk_score -= 2
        reducers.append("Security-hardening intent detected")

    if intent == "risky_change":
        risk_score += 2
        reasons.append("Destructive or high-impact intent detected")

    # -------------------------------------------------
    # 6. Environment weighting
    # -------------------------------------------------
    if env == "prod":
        risk_score *= 1.3
    elif env == "dev":
        risk_score *= 0.7

    # -------------------------------------------------
    # 7. Historical context (learning, not guessing)
    # -------------------------------------------------
    resource_types = [r["type"] for r in resources]
    history = find_similar_prs(resource_types, env)

    if history:
        risk_score += 1
        reasons.append(
            f"Historical context: {len(history)} similar change(s) observed previously"
        )

    # -------------------------------------------------
    # 8. Final risk level & confidence
    # -------------------------------------------------
    risk_level = score_to_level(risk_score)
    confidence = min(0.95, max(0.4, 0.5 + (risk_score / 10)))

    # -------------------------------------------------
    # 9. Recommendations (senior-engineer tone)
    # -------------------------------------------------
    recommendations = []

    if risk_level == "LOW":
        recommendations.append(
            "Change follows safe infrastructure patterns. Proceed with standard review."
        )

    if risk_level == "MEDIUM":
        recommendations.append(
            "Validate this change in a lower environment before promotion."
        )

    if risk_level == "HIGH":
        recommendations.extend([
            "Run this change during a defined maintenance window.",
            "Ensure a rollback plan is documented and tested.",
            "Notify dependent teams if shared infrastructure is involved."
        ])

    # -------------------------------------------------
    # 10. Build review object
    # -------------------------------------------------
    review = {
        "environment": env,
        "intent": intent,
        "risk_level": risk_level,
        "confidence": round(confidence, 2),
        "reasons": list(dict.fromkeys(reasons + reducers)),
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

    print("SUCCESS: Pattern-based, intent-aware AI review generated")
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python review.py <enriched_context.json> <ai_review.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
