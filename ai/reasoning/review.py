import json
import sys
from collections import Counter

from ai.knowledge.knowledge_loader import load_risk_patterns
from ai.reasoning.llm_enrichment import enrich_with_llm
from ai.memory.memory_store import find_similar_prs
from ai.reasoning.intent_detector import detect_intent

# -------------------------------------------------
# Helper functions
# -------------------------------------------------

def score_to_level(score: float) -> str:
    if score >= 7:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


# -------------------------------------------------
# Core Pattern Scoring Engine
# -------------------------------------------------

def assess_risk(enriched_context: dict) -> dict:
    env = enriched_context.get("environment", "dev")
    resources = enriched_context.get("resources", [])
    summary = enriched_context.get("summary", {})

    risk_patterns = load_risk_patterns()

    # -------------------------------------------------
    # 1. Collect patterns
    # -------------------------------------------------
    pattern_list = []
    for r in resources:
        pattern_list.extend(r.get("patterns", []))

    pattern_counts = Counter(pattern_list)

    # -------------------------------------------------
    # 2. Base risk score from patterns
    # -------------------------------------------------
    risk_score = 0
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
    # 3. Contextual reducers (GOOD PR SIGNALS)
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

    # VM disabled / CI-safe pattern
    vm_disabled = any(
        r["type"] == "azurerm_linux_virtual_machine" and r.get("action") == "create"
        for r in resources
    )
    if vm_disabled:
        risk_score -= 1
        reducers.append("Compute resources gated or CI-safe")

    # -------------------------------------------------
    # 4. Environment weighting
    # -------------------------------------------------
    if env == "prod":
        risk_score *= 1.3
    elif env == "dev":
        risk_score *= 0.7

    # -------------------------------------------------
    # 5. Historical context
    # -------------------------------------------------
    resource_types = [r["type"] for r in resources]
    history = find_similar_prs(resource_types, env)

    if history:
        risk_score += 1
        reasons.append(
            f"Historical context: {len(history)} similar change(s) seen before"
        )

    # -------------------------------------------------
    # 6. Final risk level & confidence
    # -------------------------------------------------
    risk_level = score_to_level(risk_score)
    confidence = min(0.95, 0.5 + (risk_score / 10))

    # -------------------------------------------------
    # 7. Human-style recommendations
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
            "Run during a maintenance window.",
            "Ensure rollback plan is documented.",
            "Notify dependent teams if applicable."
        ])

    # -------------------------------------------------
    # 8. Build final review
    # -------------------------------------------------
    review = {
        "environment": env,
        "risk_level": risk_level,
        "confidence": round(confidence, 2),
        "reasons": reasons + reducers,
        "review_comments": [],
        "recommendations": recommendations
    }

    return review


# -------------------------------------------------
# Entry point
# -------------------------------------------------

def main(input_file: str, output_file: str):
    with open(input_file, "r") as f:
        enriched_context = json.load(f)

    review = assess_risk(enriched_context)

    # LLM = explanation only
    review = enrich_with_llm(enriched_context, review)

    with open(output_file, "w") as f:
        json.dump(review, f, indent=2)

    print("SUCCESS: Pattern-based AI review generated")
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python review.py <enriched_context.json> <ai_review.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
