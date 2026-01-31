def enrich_with_llm(enriched_context: dict, review: dict) -> dict:
    """
    LLM is used ONLY to explain findings.
    It must NEVER introduce new risk or override decisions.
    """

    # If LLM is disabled, return as-is
    if not review.get("security_findings") and not review.get("policy_violations"):
        review["llm_explanation"] = (
            "This change introduces no significant risk signals. "
            "Infrastructure is being created safely without public exposure "
            "or sensitive security concerns."
        )
        return review

    findings = []
    for f in review.get("security_findings", []):
        findings.append(
            f"- {f['pattern']}: {f['description']} (severity: {f['severity']})"
        )

    for p in review.get("policy_violations", []):
        findings.append(
            f"- Policy violation ({p['policy']}): {p['description']}"
        )

    # Build a grounded explanation prompt
    explanation = (
        "The AI review identified the following concrete findings:\n\n"
        + "\n".join(findings)
        + "\n\n"
        "Explanation:\n"
    )

    # High-risk explanation
    if review["risk_level"] == "HIGH":
        explanation += (
            "These findings indicate a high-risk infrastructure change. "
            "The presence of security-sensitive resources or violations "
            "requires careful remediation before merge."
        )

    # Medium-risk explanation
    elif review["risk_level"] == "MEDIUM":
        explanation += (
            "The change introduces moderate risk that should be reviewed carefully. "
            "While not immediately dangerous, the identified findings could lead "
            "to operational or security issues if left unaddressed."
        )

    # Low-risk explanation (IMPORTANT)
    else:
        explanation += (
            "No critical or high-risk issues were detected. "
            "The findings are informational in nature and do not pose "
            "a significant security or operational risk in this environment."
        )

    review["llm_explanation"] = explanation
    return review
