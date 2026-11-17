import pytest

from app.services.risk_contract import build_public_risk_contract


@pytest.mark.parametrize(
    ("risk_score", "expected_probability", "expected_trust"),
    [
        (0, 0.0, "high"),
        (39, 0.39, "high"),
        (40, 0.4, "medium"),
        (69, 0.69, "medium"),
        (70, 0.7, "low"),
        (100, 1.0, "low"),
    ],
)
def test_build_public_risk_contract_maps_score_boundaries(
    risk_score: int,
    expected_probability: float,
    expected_trust: str,
) -> None:
    result = build_public_risk_contract(
        {
            "risk_score": risk_score,
            "trust_level": "internal-value",
            "flags": ["test_flag"],
        }
    )

    assert result == {
        "risk_score": risk_score,
        "fraud_probability": expected_probability,
        "trust_level": expected_trust,
        "flags": ["test_flag"],
    }


def test_build_public_risk_contract_does_not_mutate_internal_result() -> None:
    internal_risk = {
        "risk_score": 30,
        "trust_level": "low",
        "flags": ["vpn_detected"],
    }
    original_risk = internal_risk.copy()

    result = build_public_risk_contract(internal_risk)

    assert internal_risk == original_risk
    assert result["trust_level"] == "high"
    assert internal_risk["trust_level"] == "low"


@pytest.mark.parametrize("risk_score", [-1, 101])
def test_build_public_risk_contract_rejects_out_of_range_scores(
    risk_score: int,
) -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        build_public_risk_contract({"risk_score": risk_score})


@pytest.mark.parametrize("risk_score", [30.5, "30", True, None])
def test_build_public_risk_contract_rejects_non_integer_scores(
    risk_score: object,
) -> None:
    with pytest.raises(TypeError, match="must be an integer"):
        build_public_risk_contract({"risk_score": risk_score})
