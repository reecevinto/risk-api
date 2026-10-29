import phonenumbers
from phonenumbers import carrier, geocoder


AFRICAN_REGIONS = {
    "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "TD",
    "KM", "CG", "CD", "CI", "DJ", "EG", "GQ", "ER", "SZ", "ET",
    "GA", "GM", "GH", "GN", "GW", "KE", "LS", "LR", "LY", "MG",
    "MW", "ML", "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW",
    "ST", "SN", "SC", "SL", "SO", "ZA", "SS", "SD", "TZ", "TG",
    "TN", "UG", "ZM", "ZW",
}

LINE_TYPE_NAMES = {
    phonenumbers.PhoneNumberType.FIXED_LINE: "fixed_line",
    phonenumbers.PhoneNumberType.MOBILE: "mobile",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_line_or_mobile",
    phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium_rate",
    phonenumbers.PhoneNumberType.SHARED_COST: "shared_cost",
    phonenumbers.PhoneNumberType.VOIP: "voip",
    phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "personal_number",
    phonenumbers.PhoneNumberType.PAGER: "pager",
    phonenumbers.PhoneNumberType.UAN: "uan",
    phonenumbers.PhoneNumberType.VOICEMAIL: "voicemail",
    phonenumbers.PhoneNumberType.UNKNOWN: "unknown",
}


def _empty_phone_result() -> dict:
    return {
        "phone_valid": False,
        "country": None,
        "carrier": None,
        "risk_flag": "high",
        "line_type": "unknown",
        "carrier_source": "phonenumbers_metadata",
        "is_african_region": False,
    }


def analyze_phone(phone_number: str) -> dict:
    if not isinstance(phone_number, str) or not phone_number.strip():
        return _empty_phone_result()

    try:
        parsed_number = phonenumbers.parse(phone_number.strip(), None)
    except (phonenumbers.NumberParseException, ValueError, TypeError):
        return _empty_phone_result()

    valid = phonenumbers.is_valid_number(parsed_number)
    country = geocoder.region_code_for_number(parsed_number) or None
    carrier_name = carrier.name_for_number(parsed_number, "en")
    parsed_line_type = phonenumbers.number_type(parsed_number)

    return {
        "phone_valid": valid,
        "country": country,
        "carrier": carrier_name or "unknown",
        "risk_flag": "low" if valid else "high",
        "line_type": LINE_TYPE_NAMES.get(parsed_line_type, "unknown"),
        "carrier_source": "phonenumbers_metadata",
        "is_african_region": country in AFRICAN_REGIONS,
    }
