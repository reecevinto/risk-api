def compute_risk(phone_data=None, email_data=None, ip_data=None):
    score = 0
    flags = []

    # -------------------------
    # PHONE SCORING
    # -------------------------
    if phone_data:
        if phone_data.get("risk_flag") == "high":
            score += 30
            flags.append("phone_invalid")

    # -------------------------
    # EMAIL SCORING
    # -------------------------
    if email_data:
        if not email_data.get("valid_format"):
            score += 30
            flags.append("email_invalid")

        if email_data.get("disposable"):
            score += 25
            flags.append("disposable_email")

        if not email_data.get("mx_records"):
            score += 20
            flags.append("no_mx_records")

    # -------------------------
    # IP SCORING
    # -------------------------
    if ip_data:
        if ip_data.get("is_proxy"):
            score += 30
            flags.append("vpn_detected")

        if ip_data.get("is_hosting"):
            score += 25
            flags.append("datacenter_ip")

        if ip_data.get("country_mismatch"):
            score += 15
            flags.append("country_mismatch")

    # -------------------------
    # NORMALIZE SCORE (0–100)
    # -------------------------
    if score > 100:
        score = 100

    # -------------------------
    # TRUST LEVEL
    # -------------------------
    if score >= 70:
        trust = "high_risk"
    elif score >= 40:
        trust = "medium"
    else:
        trust = "low"

    return {
        "risk_score": score,
        "trust_level": trust,
        "flags": flags
    }