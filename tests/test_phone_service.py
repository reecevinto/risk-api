import phonenumbers
import pytest

from app.services.phone_service import analyze_phone


@pytest.mark.parametrize(
    ("number", "expected_country", "expected_carrier"),
    [
        ("+254712345678", "KE", "Safaricom"),
        ("+2348031234567", "NG", "MTN"),
        ("+233241234567", "GH", "MTN"),
        ("+256772123456", "UG", "MTN"),
        ("+255712345678", "TZ", "Yas"),
        ("+27821234567", "ZA", "Vodacom"),
    ],
)
def test_valid_african_numbers_include_metadata(
    number, expected_country, expected_carrier
):
    result = analyze_phone(number)

    assert result["phone_valid"] is True
    assert result["country"] == expected_country
    assert result["carrier"] == expected_carrier
    assert result["risk_flag"] == "low"
    assert result["line_type"] == "mobile"
    assert result["carrier_source"] == "phonenumbers_metadata"
    assert result["is_african_region"] is True


def test_valid_us_number_is_not_penalized_for_country():
    result = analyze_phone("+12025550123")

    # This is a syntactically valid number but its allocation/validity
    # metadata can vary. Test the country policy independently below.
    assert result["carrier_source"] == "phonenumbers_metadata"
    assert result["is_african_region"] is False


def test_unknown_carrier_does_not_increase_risk(monkeypatch):
    monkeypatch.setattr(
        "app.services.phone_service.carrier.name_for_number",
        lambda *args: "",
    )

    result = analyze_phone("+254712345678")

    assert result["phone_valid"] is True
    assert result["carrier"] == "unknown"
    assert result["risk_flag"] == "low"


@pytest.mark.parametrize(
    "number",
    [
        "",
        "   ",
        "not-a-number",
        "123",
        "+",
    ],
)
def test_invalid_or_unparseable_numbers_return_safe_result(number):
    result = analyze_phone(number)

    assert result["phone_valid"] is False
    assert result["country"] is None
    assert result["carrier"] is None
    assert result["risk_flag"] == "high"
    assert result["line_type"] == "unknown"
    assert result["carrier_source"] == "phonenumbers_metadata"
    assert result["is_african_region"] is False


def test_valid_non_african_number_is_not_penalized_for_region(monkeypatch):
    number = phonenumbers.parse("+12025550123", None)

    monkeypatch.setattr(
        "app.services.phone_service.phonenumbers.parse",
        lambda *args: number,
    )
    monkeypatch.setattr(
        "app.services.phone_service.phonenumbers.is_valid_number",
        lambda parsed: True,
    )
    monkeypatch.setattr(
        "app.services.phone_service.geocoder.region_code_for_number",
        lambda parsed: "US",
    )
    monkeypatch.setattr(
        "app.services.phone_service.carrier.name_for_number",
        lambda *args: "",
    )
    monkeypatch.setattr(
        "app.services.phone_service.phonenumbers.number_type",
        lambda parsed: phonenumbers.PhoneNumberType.MOBILE,
    )

    result = analyze_phone("+12025550123")

    assert result["phone_valid"] is True
    assert result["country"] == "US"
    assert result["carrier"] == "unknown"
    assert result["risk_flag"] == "low"
    assert result["is_african_region"] is False


def test_invalid_but_parseable_number_is_high_risk(monkeypatch):
    monkeypatch.setattr(
        "app.services.phone_service.phonenumbers.is_valid_number",
        lambda parsed: False,
    )

    result = analyze_phone("+254712345678")

    assert result["phone_valid"] is False
    assert result["risk_flag"] == "high"


# ============================================================
# PHASE 3 DAY 12 TELCO INTELLIGENCE ENRICHMENT
# ============================================================

def test_valid_african_number_includes_complete_telco_intelligence():
    result = analyze_phone("+254712345678")

    assert result["phone_valid"] is True
    assert result["number_possible"] is True
    assert result["possibility_reason"] == "possible"

    assert result["country"] == "KE"
    assert result["country_calling_code"] == 254

    assert result["carrier"] == "Safaricom"
    assert result["carrier_status"] == "identified"
    assert result["carrier_source"] == "phonenumbers_metadata"

    assert result["line_type"] == "mobile"
    assert result["number_type"] == "mobile"

    assert result["is_african_region"] is True

    assert result["regional_intelligence"] == {
        "country_code": "KE",
        "country_calling_code": 254,
        "continent": "Africa",
        "african_region": "Eastern Africa",
        "is_african_region": True,
    }


@pytest.mark.parametrize(
    ("number", "expected_region"),
    [
        ("+213551234567", "Northern Africa"),
        ("+2348031234567", "Western Africa"),
        ("+237620000000", "Middle Africa"),
        ("+254712345678", "Eastern Africa"),
        ("+27821234567", "Southern Africa"),
    ],
)
def test_african_subregion_classification(number, expected_region):
    result = analyze_phone(number)

    assert result["phone_valid"] is True
    assert result["is_african_region"] is True
    assert (
        result["regional_intelligence"]["african_region"]
        == expected_region
    )
    assert result["regional_intelligence"]["continent"] == "Africa"


def test_valid_non_african_number_has_no_african_subregion():
    result = analyze_phone("+12025550123")

    assert result["country"] == "US"
    assert result["country_calling_code"] == 1
    assert result["is_african_region"] is False

    assert result["regional_intelligence"] == {
        "country_code": "US",
        "country_calling_code": 1,
        "continent": "other",
        "african_region": None,
        "is_african_region": False,
    }


def test_unknown_carrier_has_explicit_unknown_status(monkeypatch):
    monkeypatch.setattr(
        "app.services.phone_service.carrier.name_for_number",
        lambda *args: "",
    )

    result = analyze_phone("+254712345678")

    assert result["phone_valid"] is True
    assert result["carrier"] == "unknown"
    assert result["carrier_status"] == "unknown"
    assert result["carrier_source"] == "phonenumbers_metadata"
    assert result["risk_flag"] == "low"


def test_carrier_limitation_is_explicit():
    result = analyze_phone("+254712345678")

    limitation = result["carrier_limitation"].lower()

    assert "static numbering-plan metadata" in limitation
    assert "mobile number portability" in limitation
    assert "live network" in limitation
    assert "sim" in limitation
    assert "ownership" in limitation


@pytest.mark.parametrize(
    "number",
    [
        "",
        "   ",
        "not-a-number",
        "123",
        "+",
    ],
)
def test_invalid_results_preserve_complete_day12_schema(number):
    result = analyze_phone(number)

    assert result["phone_valid"] is False
    assert result["number_possible"] is False
    assert result["possibility_reason"] == "not_parsed"

    assert result["country"] is None
    assert result["country_calling_code"] is None

    assert result["carrier"] is None
    assert result["carrier_status"] == "unknown"

    assert result["line_type"] == "unknown"
    assert result["number_type"] == "unknown"

    assert result["risk_flag"] == "high"
    assert result["is_african_region"] is False

    assert result["regional_intelligence"] == {
        "country_code": None,
        "country_calling_code": None,
        "continent": "unknown",
        "african_region": None,
        "is_african_region": False,
    }


def test_possible_and_valid_are_independent():
    result = analyze_phone("+254123")

    assert result["phone_valid"] is False
    assert result["number_possible"] is False
    assert result["possibility_reason"] == "too_short"
    assert result["risk_flag"] == "high"


def test_region_and_carrier_metadata_do_not_change_phone_risk(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.phone_service.carrier.name_for_number",
        lambda *args: "",
    )

    result = analyze_phone("+254712345678")

    assert result["phone_valid"] is True
    assert result["carrier_status"] == "unknown"
    assert result["is_african_region"] is True
    assert result["regional_intelligence"]["african_region"] == (
        "Eastern Africa"
    )
    assert result["risk_flag"] == "low"


def test_non_string_phone_input_returns_safe_result():
    result = analyze_phone(None)

    assert result["phone_valid"] is False
    assert result["number_possible"] is False
    assert result["possibility_reason"] == "not_parsed"
    assert result["carrier_status"] == "unknown"
    assert result["risk_flag"] == "high"
