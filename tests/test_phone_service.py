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
