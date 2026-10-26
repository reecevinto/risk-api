import ipaddress

import requests

from app.core import config


IPINFO_LOOKUP_URL = "https://api.ipinfo.io/lookup/{ip}"
IPINFO_PRIVACY_FIELDS = (
    "is_proxy",
    "is_vpn",
    "is_tor",
    "is_relay",
)


def _base_result(ip: str) -> dict:
    return {
        "ip": ip,
        "status": "unavailable",
        "error_code": None,
        "country": None,
        "country_code": None,
        "region": None,
        "city": None,
        "isp": None,
        "asn": None,
        "organization": None,
        "network_type": None,
        "is_proxy": None,
        "is_vpn": None,
        "is_tor": None,
        "is_relay": None,
        "is_anonymous": None,
        "is_hosting": False,
        "is_residential": None,
        "is_mobile": None,
        "is_anycast": None,
        "is_satellite": None,
        "privacy_signals_available": False,
        "country_mismatch": False,
        "risk_flag": "unknown",
    }


def _unavailable(result: dict, error_code: str) -> dict:
    result["status"] = "unavailable"
    result["error_code"] = error_code
    result["risk_flag"] = "unknown"
    return result


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None


def _country_mismatch(
    user_country: str | None,
    country: str | None,
    country_code: str | None,
) -> bool:
    if not isinstance(user_country, str) or not user_country.strip():
        return False

    supplied_country = user_country.strip().casefold()

    known_countries = {
        value.casefold()
        for value in (country, country_code)
        if isinstance(value, str) and value.strip()
    }

    return (
        bool(known_countries)
        and supplied_country not in known_countries
    )


def analyze_ip(ip: str, user_country: str = None) -> dict:
    """Enrich a public IP with IPinfo Plus geolocation and privacy signals."""
    result = _base_result(ip)

    try:
        parsed_ip = ipaddress.ip_address(ip)
    except (ValueError, TypeError):
        result["status"] = "invalid"
        result["error_code"] = "invalid_ip"
        return result

    if not parsed_ip.is_global or parsed_ip.is_multicast:
        result["status"] = "not_public"
        result["error_code"] = "non_public_ip"
        return result

    token = config.IPINFO_TOKEN

    if not token or not token.strip():
        return _unavailable(result, "provider_not_configured")

    try:
        response = requests.get(
            IPINFO_LOOKUP_URL.format(ip=parsed_ip.compressed),
            params={"token": token},
            timeout=config.IPINFO_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

    except requests.Timeout:
        return _unavailable(result, "provider_timeout")

    except requests.HTTPError as exc:
        status_code = (
            exc.response.status_code
            if exc.response is not None
            else None
        )

        if status_code == 429:
            return _unavailable(
                result,
                "provider_rate_limited",
            )

        if status_code in (401, 403):
            return _unavailable(
                result,
                "provider_auth_error",
            )

        return _unavailable(
            result,
            "provider_http_error",
        )

    except requests.exceptions.JSONDecodeError:
        return _unavailable(
            result,
            "provider_invalid_response",
        )

    except requests.RequestException:
        return _unavailable(
            result,
            "provider_request_error",
        )

    except (ValueError, TypeError):
        return _unavailable(
            result,
            "provider_invalid_response",
        )

    if not isinstance(data, dict):
        return _unavailable(
            result,
            "provider_invalid_response",
        )

    geo = data.get("geo")
    network = data.get("as")
    anonymous = data.get("anonymous")

    geo = geo if isinstance(geo, dict) else {}
    network = network if isinstance(network, dict) else {}
    anonymous = (
        anonymous
        if isinstance(anonymous, dict)
        else {}
    )

    result.update(
        {
            "status": "ok",
            "error_code": None,
            "country": _optional_string(geo.get("country")),
            "country_code": _optional_string(geo.get("country_code")),
            "region": _optional_string(geo.get("region")),
            "city": _optional_string(geo.get("city")),
            "isp": _optional_string(network.get("name")),
            "asn": _optional_string(network.get("asn")),
            "organization": _optional_string(network.get("name")),
            "network_type": _optional_string(network.get("type")),
        }
    )

    for field in IPINFO_PRIVACY_FIELDS:
        value = anonymous.get(field)
        result[field] = value if isinstance(value, bool) else None

    result["privacy_signals_available"] = all(
        field in anonymous
        and isinstance(anonymous[field], bool)
        for field in IPINFO_PRIVACY_FIELDS
    )

    result["is_anonymous"] = (
        data.get("is_anonymous")
        if isinstance(data.get("is_anonymous"), bool)
        else None
    )

    result["is_hosting"] = (
        data.get("is_hosting") is True
    )

    for field in (
        "is_mobile",
        "is_anycast",
        "is_satellite",
    ):
        value = data.get(field)
        result[field] = (
            value
            if isinstance(value, bool)
            else None
        )

    # ASN network type alone does not establish residential usage.
    # Only an explicitly identified hosting IP is classified as non-residential.
    if result["is_hosting"]:
        result["is_residential"] = False

    result["country_mismatch"] = _country_mismatch(
        user_country,
        result["country"],
        result["country_code"],
    )

    risk_score = 0

    if any(
        result[field]
        for field in (
            "is_proxy",
            "is_vpn",
            "is_tor",
            "is_relay",
        )
    ):
        risk_score += 2

    if result["is_hosting"]:
        risk_score += 2

    if result["country_mismatch"]:
        risk_score += 1

    result["risk_flag"] = (
        "high"
        if risk_score >= 3
        else "medium"
        if risk_score == 2
        else "low"
    )

    return result
