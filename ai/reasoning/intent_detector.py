def detect_intent(enriched_context: dict) -> str:
    """
    Infer high-level intent of the PR based on change patterns.
    This does NOT decide risk — only tone & expectations.
    """

    resources = enriched_context.get("resources", [])
    summary = enriched_context.get("summary", {})

    actions = [r["action"] for r in resources]
    patterns = set(p for r in resources for p in r.get("patterns", []))

    # -------------------------------------------------
    # Bootstrap: first-time infra creation
    # -------------------------------------------------
    if summary.get("create", 0) > 0 and summary.get("update", 0) == 0:
        return "bootstrap"

    # -------------------------------------------------
    # Security hardening
    # -------------------------------------------------
    if "identity_boundary" in patterns and "public_exposure" not in patterns:
        return "security_hardening"

    # -------------------------------------------------
    # Refactor / restructure
    # -------------------------------------------------
    if summary.get("update", 0) > 0 and summary.get("delete", 0) == 0:
        return "refactor"

    # -------------------------------------------------
    # Risky / destructive change
    # -------------------------------------------------
    if summary.get("delete", 0) > 0:
        return "risky_change"

    return "unknown"
