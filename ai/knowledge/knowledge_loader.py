import json
from pathlib import Path

# Base directory of this file
BASE_PATH = Path(__file__).parent


# -------------------------------------------------
# Risk Pattern Definitions
# -------------------------------------------------

def load_risk_patterns() -> dict:
    """
    Loads universal risk patterns and their base scores.
    These patterns are cloud-agnostic and stable.
    """
    with open(BASE_PATH / "risk_patterns.json", "r") as f:
        data = json.load(f)
    return data.get("patterns", {})


# -------------------------------------------------
# Service → Capability Mapping
# -------------------------------------------------

def load_service_capabilities() -> dict:
    """
    Maps Terraform resource types to risk patterns.
    Adding a new Azure service requires only updating JSON.
    """
    with open(BASE_PATH / "service_capabilities.json", "r") as f:
        return json.load(f)


# -------------------------------------------------
# Security Severity Definitions
# -------------------------------------------------

def load_security_severity() -> dict:
    """
    Defines security severity per risk pattern.
    Used to distinguish LOW / MEDIUM / HIGH / CRITICAL security issues.
    """
    with open(BASE_PATH / "security_severity.json", "r") as f:
        return json.load(f)


# -------------------------------------------------
# Blocking Rules Definitions
# -------------------------------------------------

def load_blocking_rules() -> dict:
    """
    Loads blocking rules from the policies directory.
    These rules define which risk patterns should block deployments.
    """
    with open(BASE_PATH / "../policies/blocking_rules.json", "r") as f:
        return json.load(f)
