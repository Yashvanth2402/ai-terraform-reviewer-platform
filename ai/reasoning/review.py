import json
import sys


def assess_risk(ctx: dict):
    caps = ctx["capabilities_detected"]
    summary = ctx["summary"]

    reasons = []
    recommendations = []
    confidence = 0.6

    is_create_only = (
        summary["create"] > 0 and
        summary["update"] == 0 and
        summary["delete"] == 0
    )

    # -------------------------------
    # 🔴 DATA PLANE + PUBLIC EXPOSURE
    # -------------------------------
    if caps.get("data_plane") and caps.get("public_exposure"):
        return {
            "risk_level": "HIGH",
            "decision": "BLOCK",
            "confidence": 0.95,
            "reasons": [
                "Public data plane exposure detected"
            ],
            "recommendations": [
                "Disable public access to data services",
                "Use private endpoints",
                "Restrict network access",
                "Require security approval"
            ]
        }

    # --------------------------------
    # 🟠 ACTIVE INFRA (COMPUTE / CONTROL)
    # --------------------------------
    if is_create_only and (caps.get("compute_plane") or caps.get("control_plane")):
        return {
            "risk_level": "MEDIUM",
            "decision": "WARN",
            "confidence": 0.85,
            "reasons": [
                "Active infrastructure introduced requiring human review"
            ],
            "recommendations": [
                "Ensure hardening standards are followed",
                "Confirm this is intended for the environment"
            ]
        }

    # --------------------------------
    # 🟢 SCAFFOLD / NETWORK ONLY
    # --------------------------------
    return {
        "risk_level": "LOW",
        "decision": "PASS",
        "confidence": confidence,
        "reasons": [
            "Create-only scaffold infrastructure without public exposure"
        ],
        "recommendations": [
            "LGTM from an infrastructure safety perspective."
        ]
    }


def main(input_file, output_file):
    with open(input_file) as f:
        ctx = json.load(f)

    review = assess_risk(ctx)

    with open(output_file, "w") as f:
        json.dump(review, f, indent=2)

    print("SUCCESS: Terraform AI review generated")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
