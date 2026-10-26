import pytest

from app.services.risk_engine import compute_risk


def test_vpn_is_scored_without_double_counting_generic_proxy():
    result = compute_risk(
        ip_data={
            "status": "ok",
            "is_vpn": True,
            "is_proxy": True,
        }
    )

    assert result["risk_score"] == 30
    assert result["trust_level"] == "low"
    assert result["flags"] == ["vpn_detected"]


def test_generic_proxy_has_separate_flag_and_score():
    result = compute_risk(
        ip_data={
            "status": "ok",
            "is_proxy": True,
            "is_vpn": False,
        }
    )

    assert result["risk_score"] == 20
    assert result["trust_level"] == "low"
    assert result["flags"] == ["proxy_detected"]


def test_tor_detection():
    result = compute_risk(
        ip_data={
            "status": "ok",
            "is_tor": True,
        }
    )

    assert result["risk_score"] == 30
    assert result["flags"] == ["tor_detected"]


def test_relay_detection():
    result = compute_risk(
        ip_data={
            "status": "ok",
            "is_relay": True,
        }
    )

    assert result["risk_score"] == 15
    assert result["flags"] == ["relay_detected"]


def test_hosting_ip_detection():
    result = compute_risk(
        ip_data={
            "status": "ok",
            "is_hosting": True,
        }
    )

    assert result["risk_score"] == 25
    assert result["flags"] == ["datacenter_ip"]


def test_country_mismatch_detection():
    result = compute_risk(
        ip_data={
            "status": "ok",
            "country_mismatch": True,
        }
    )

    assert result["risk_score"] == 15
    assert result["flags"] == ["country_mismatch"]


def test_multiple_ip_signals_accumulate_correctly():
    result = compute_risk(
        ip_data={
            "status": "ok",
            "is_vpn": True,
            "is_proxy": True,
            "is_tor": True,
            "is_relay": True,
            "is_hosting": True,
            "country_mismatch": True,
        }
    )

    # VPN 30 + Tor 30 + relay 15 + hosting 25 + mismatch 15.
    # The generic proxy is not counted separately when VPN is true.
    # The resulting total is capped at 100.
    assert result["risk_score"] == 100
    assert result["trust_level"] == "high_risk"
    assert result["flags"] == [
        "vpn_detected",
        "tor_detected",
        "relay_detected",
        "datacenter_ip",
        "country_mismatch",
    ]


def test_unavailable_ip_data_does_not_increase_risk():
    result = compute_risk(
        ip_data={
            "status": "unavailable",
            "is_vpn": True,
            "is_proxy": True,
            "is_hosting": True,
            "country_mismatch": True,
        }
    )

    assert result["risk_score"] == 0
    assert result["trust_level"] == "low"
    assert result["flags"] == []


def test_invalid_ip_data_does_not_increase_risk():
    result = compute_risk(
        ip_data={
            "status": "invalid",
            "is_vpn": True,
            "is_hosting": True,
        }
    )

    assert result["risk_score"] == 0
    assert result["flags"] == []


def test_non_public_ip_data_does_not_increase_risk():
    result = compute_risk(
        ip_data={
            "status": "not_public",
            "is_proxy": True,
            "is_hosting": True,
        }
    )

    assert result["risk_score"] == 0
    assert result["flags"] == []


def test_legacy_ip_data_without_status_remains_supported():
    result = compute_risk(
        ip_data={
            "is_proxy": True,
            "is_hosting": True,
            "country_mismatch": True,
        }
    )

    assert result["risk_score"] == 60
    assert result["trust_level"] == "medium"
    assert result["flags"] == [
        "proxy_detected",
        "datacenter_ip",
        "country_mismatch",
    ]


def test_phone_and_email_scoring_remain_unchanged():
    result = compute_risk(
        phone_data={"risk_flag": "high"},
        email_data={
            "valid_format": False,
            "disposable": True,
            "mx_records": False,
        },
    )

    assert result["risk_score"] == 100
    assert result["trust_level"] == "high_risk"
    assert result["flags"] == [
        "phone_invalid",
        "email_invalid",
        "disposable_email",
        "no_mx_records",
    ]


def test_combined_risk_score_is_capped_at_100():
    result = compute_risk(
        phone_data={"risk_flag": "high"},
        email_data={
            "valid_format": False,
            "disposable": True,
            "mx_records": False,
        },
        ip_data={
            "status": "ok",
            "is_vpn": True,
            "is_tor": True,
            "is_relay": True,
            "is_hosting": True,
            "country_mismatch": True,
        },
    )

    assert result["risk_score"] == 100
    assert result["trust_level"] == "high_risk"


def test_trust_level_thresholds_are_preserved():
    low = compute_risk(
        ip_data={"status": "ok", "is_proxy": True}
    )
    medium = compute_risk(
        ip_data={"status": "ok", "is_hosting": True, "is_vpn": True}
    )
    high = compute_risk(
        ip_data={
            "status": "ok",
            "is_hosting": True,
            "is_vpn": True,
            "is_tor": True,
        }
    )

    assert low["risk_score"] == 20
    assert low["trust_level"] == "low"

    assert medium["risk_score"] == 55
    assert medium["trust_level"] == "medium"

    assert high["risk_score"] == 85
    assert high["trust_level"] == "high_risk"


@pytest.mark.parametrize(
    "status",
    ["error", "malformed", "success", None],
)
def test_unexpected_ip_status_does_not_increase_risk(status):
    result = compute_risk(
        ip_data={
            "status": status,
            "is_vpn": True,
            "is_proxy": True,
            "is_hosting": True,
            "country_mismatch": True,
        }
    )

    assert result["risk_score"] == 0
    assert result["trust_level"] == "low"
    assert result["flags"] == []
