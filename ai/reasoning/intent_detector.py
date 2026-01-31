def detect_intent(enriched_context: dict) -> str:
    """
    Detects the intent of a Terraform PR based on actions and patterns.

    Possible intents:
    - bootstrap
    - security_hardening
    - risky_change
    - mixed_change
    """

    resources = enriched_context.get("resources", [])
    summary = enriched_context.get("summary", {})

    creates = summary.get("create", 0)
    updates = summary.get("update", 0)
    deletes = summary.get("delete", 0)

    # -----------------------------------------
    # 1️⃣ Bootstrap infrastructure
    # -----------------------------------------
    if creates > 0 and updates == 0 and deletes == 0:
        return "bootstrap"

    # -----------------------------------------
    # 2️⃣ Destructive / risky changes
    # -----------------------------------------
    if deletes > 0:
        return "risky_change"

    # -----------------------------------------
    # 3️⃣ Security hardening
    # -----------------------------------------
    all_patterns = []
    for r in resources:
        all_patterns.extend(r.get("patterns", []))

    if (
        "identity_boundary" in all_patterns
        and "public_exposure" not in all_patterns
        and updates > 0
        and deletes == 0
    ):
        return "security_hardening"

    # -----------------------------------------
    # 4️⃣ Mixed / unclear changes
    # -----------------------------------------
    return "mixed_change"
