import requests

VPN_KEYWORDS = ["vpn", "proxy", "tor", "hosting", "datacenter"]


def analyze_ip(ip: str, user_country: str = None):
    result = {
        "ip": ip,
        "country": None,
        "city": None,
        "isp": None,
        "is_proxy": False,
        "is_hosting": False,
        "country_mismatch": False,
        "risk_flag": "low"
    }

    try:
        response = requests.get(f"http://ip-api.com/json/{ip}")
        data = response.json()

        if data["status"] != "success":
            result["risk_flag"] = "high"
            return result

        # -------------------------
        # GEO DATA
        # -------------------------
        result["country"] = data.get("country")
        result["city"] = data.get("city")
        result["isp"] = data.get("isp")

        # -------------------------
        # PROXY / VPN DETECTION
        # -------------------------
        isp_lower = (data.get("isp") or "").lower()

        if any(k in isp_lower for k in VPN_KEYWORDS):
            result["is_proxy"] = True

        if data.get("hosting") is True:
            result["is_hosting"] = True

        if data.get("proxy") is True:
            result["is_proxy"] = True

        # -------------------------
        # COUNTRY MISMATCH LOGIC
        # -------------------------
        if user_country:
            if result["country"] and user_country.lower() != result["country"].lower():
                result["country_mismatch"] = True

        # -------------------------
        # RISK SCORING
        # -------------------------
        risk_score = 0

        if result["is_proxy"]:
            risk_score += 2

        if result["is_hosting"]:
            risk_score += 2

        if result["country_mismatch"]:
            risk_score += 1

        result["risk_flag"] = (
            "high" if risk_score >= 3 else
            "medium" if risk_score == 2 else
            "low"
        )

    except Exception:
        result["risk_flag"] = "high"

    return result