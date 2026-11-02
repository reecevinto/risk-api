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


AFRICAN_SUBREGIONS = {
    "Northern Africa": {
        "DZ", "EG", "LY", "MA", "SD", "TN",
    },
    "Western Africa": {
        "BJ", "BF", "CV", "CI", "GM", "GH", "GN", "GW",
        "LR", "ML", "MR", "NE", "NG", "SN", "SL", "TG",
    },
    "Middle Africa": {
        "AO", "CM", "CF", "TD", "CG", "CD", "GQ", "GA", "ST",
    },
    "Eastern Africa": {
        "BI", "KM", "DJ", "ER", "ET", "KE", "MG", "MW",
        "MU", "MZ", "RW", "SC", "SO", "SS", "TZ", "UG",
        "ZM", "ZW",
    },
    "Southern Africa": {
        "BW", "SZ", "LS", "NA", "ZA",
    },
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


POSSIBILITY_REASONS = {
    phonenumbers.ValidationResult.IS_POSSIBLE: "possible",
    phonenumbers.ValidationResult.IS_POSSIBLE_LOCAL_ONLY: "possible_local_only",
    phonenumbers.ValidationResult.INVALID_COUNTRY_CODE: "invalid_country_code",
    phonenumbers.ValidationResult.TOO_SHORT: "too_short",
    phonenumbers.ValidationResult.TOO_LONG: "too_long",
}


CARRIER_LIMITATION = (
    "Carrier attribution uses static numbering-plan metadata. "
    "It may reflect the original number allocation rather than the "
    "current operator because of mobile number portability. "
    "It does not verify the live network, SIM, subscriber, or ownership."
)


def _regional_intelligence(
    country: str | None,
    country_calling_code: int | None,
) -> dict:
    subregion = None

    if country:
        for region_name, countries in AFRICAN_SUBREGIONS.items():
            if country in countries:
                subregion = region_name
                break

    is_african = country in AFRICAN_REGIONS

    return {
        "country_code": country,
        "country_calling_code": country_calling_code,
        "continent": (
            "Africa"
            if is_african
            else "other"
            if country
            else "unknown"
        ),
        "african_region": subregion,
        "is_african_region": is_african,
    }


def _empty_phone_result() -> dict:
    return {
        "phone_valid": False,
        "number_possible": False,
        "possibility_reason": "not_parsed",
        "country": None,
        "country_calling_code": None,
        "carrier": None,
        "carrier_source": "phonenumbers_metadata",
        "carrier_status": "unknown",
        "carrier_limitation": CARRIER_LIMITATION,
        "risk_flag": "high",
        "line_type": "unknown",
        "number_type": "unknown",
        "is_african_region": False,
        "regional_intelligence": _regional_intelligence(None, None),
    }


def analyze_phone(phone_number: str) -> dict:
    """
    Enrich a phone number using locally installed numbering-plan metadata.

    Carrier attribution is informational and does not establish the
    subscriber's current mobile operator or verify a live SIM.
    """
    if not isinstance(phone_number, str) or not phone_number.strip():
        return _empty_phone_result()

    try:
        parsed_number = phonenumbers.parse(phone_number.strip(), None)
    except (phonenumbers.NumberParseException, ValueError, TypeError):
        return _empty_phone_result()

    valid = phonenumbers.is_valid_number(parsed_number)
    possible_reason_code = (
        phonenumbers.is_possible_number_with_reason(parsed_number)
    )
    possible = phonenumbers.is_possible_number(parsed_number)

    country = geocoder.region_code_for_number(parsed_number) or None
    carrier_name = carrier.name_for_number(parsed_number, "en") or None

    parsed_line_type = phonenumbers.number_type(parsed_number)
    line_type = LINE_TYPE_NAMES.get(parsed_line_type, "unknown")

    calling_code = parsed_number.country_code or None

    return {
        "phone_valid": valid,
        "number_possible": possible,
        "possibility_reason": POSSIBILITY_REASONS.get(
            possible_reason_code,
            "unknown",
        ),
        "country": country,
        "country_calling_code": calling_code,
        "carrier": carrier_name or "unknown",
        "carrier_source": "phonenumbers_metadata",
        "carrier_status": (
            "identified"
            if carrier_name
            else "unknown"
        ),
        "carrier_limitation": CARRIER_LIMITATION,
        "risk_flag": "low" if valid else "high",
        "line_type": line_type,
        "number_type": line_type,
        "is_african_region": country in AFRICAN_REGIONS,
        "regional_intelligence": _regional_intelligence(
            country,
            calling_code,
        ),
    }
