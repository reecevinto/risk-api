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

        # Penalize confirmed missing MX records, not DNS lookup failures.
        # Preserve original behavior for legacy results without mx_status.
        mx_status = email_data.get("mx_status")

        if mx_status == "missing":
            score += 20
            flags.append("no_mx_records")
        elif (
            "mx_status" not in email_data
            and not email_data.get("mx_records")
        ):
            score += 20
            flags.append("no_mx_records")

    # -------------------------
    # IP SCORING
    # -------------------------
    # Score successful lookups and legacy results without a status.
    # Unknown or failed lookup states must not increase IP risk.
    if ip_data and (
        ip_data.get("status") == "ok"
        or "status" not in ip_data
    ):
        is_vpn = ip_data.get("is_vpn") is True
        is_tor = ip_data.get("is_tor") is True
        is_relay = ip_data.get("is_relay") is True
        is_proxy = ip_data.get("is_proxy") is True

        if is_vpn:
            score += 30
            flags.append("vpn_detected")

        if is_tor:
            score += 30
            flags.append("tor_detected")

        if is_relay:
            score += 15
            flags.append("relay_detected")

        # A VPN should not also receive the generic proxy penalty.
        if is_proxy and not is_vpn:
            score += 20
            flags.append("proxy_detected")

        if ip_data.get("is_hosting") is True:
            score += 25
            flags.append("datacenter_ip")

        if ip_data.get("country_mismatch") is True:
            score += 15
            flags.append("country_mismatch")

    # -------------------------
    # NORMALIZE SCORE (0-100)
    # -------------------------
    score = min(score, 100)

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
        "flags": flags,
    }