import json
from ai.llm.llm_client import AzureLLMClient
from ai.llm.prompts import SYSTEM_PROMPT, build_user_prompt


def enrich_with_llm(enriched_context: dict, ai_review: dict) -> dict:
    """
    Uses Azure OpenAI ONLY to enhance explanations.
    DOES NOT change risk, confidence, or decisions.
    """

    try:
        client = AzureLLMClient()

        explanation = client.explain_risk(
            SYSTEM_PROMPT,
            build_user_prompt(enriched_context, ai_review)
        )

        ai_review["llm_explanation"] = explanation

    except Exception as e:
        # SAFE FALLBACK — never break CI
        ai_review["llm_explanation"] = (
            "LLM explanation unavailable. "
            "Proceeding with deterministic review."
        )

    return ai_review
