from typing import Any


def build_public_risk_contract(risk: dict[str, Any]) -> dict[str, Any]:
    """Build the public risk contract without modifying the internal result.

    fraud_probability is a normalized risk indicator (risk_score / 100),
    not a statistically calibrated probability of fraud.
    """
    risk_score = risk["risk_score"]

    if not isinstance(risk_score, int) or isinstance(risk_score, bool):
        raise TypeError("risk_score must be an integer")

    if not 0 <= risk_score <= 100:
        raise ValueError("risk_score must be between 0 and 100")

    if risk_score >= 70:
        trust_level = "low"
    elif risk_score >= 40:
        trust_level = "medium"
    else:
        trust_level = "high"

    return {
        "risk_score": risk_score,
        "fraud_probability": risk_score / 100,
        "trust_level": trust_level,
        "flags": risk.get("flags", []),
    }
