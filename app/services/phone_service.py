import phonenumbers
from phonenumbers import carrier, geocoder


def analyze_phone(phone_number: str):
    try:
        parsed_number = phonenumbers.parse(phone_number, None)

        # Validate number
        valid = phonenumbers.is_valid_number(parsed_number)

        # Country
        country = geocoder.region_code_for_number(parsed_number)

        # Carrier (basic)
        carrier_name = carrier.name_for_number(parsed_number, "en")

        # Risk logic (simple V1 rule)
        risk_flag = "low"

        if not valid:
            risk_flag = "high"

        if country not in ["KE", "US", "GB"]:
            risk_flag = "medium"

        return {
            "phone_valid": valid,
            "country": country,
            "carrier": carrier_name if carrier_name else "unknown",
            "risk_flag": risk_flag
        }

    except Exception:
        return {
            "phone_valid": False,
            "country": None,
            "carrier": None,
            "risk_flag": "high"
        }