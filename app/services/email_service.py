import dns.resolver
from email_validator import EmailNotValidError, validate_email

# Curated starter list. This is not intended to be an exhaustive feed.
DISPOSABLE_DOMAINS = {
    "10minutemail.com",
    "10minemail.com",
    "dispostable.com",
    "emailondeck.com",
    "fakeinbox.com",
    "getnada.com",
    "guerrillamail.com",
    "maildrop.cc",
    "mailinator.com",
    "mailnesia.com",
    "mintemail.com",
    "mohmal.com",
    "sharklasers.com",
    "tempmail.com",
    "temp-mail.org",
    "throwawaymail.com",
    "trashmail.com",
    "yopmail.com",
}

DNS_LOOKUP_TIMEOUT_SECONDS = 2.0


def _is_disposable_domain(domain: str) -> bool:
    """Match known disposable domains and their subdomains."""
    return any(
        domain == disposable_domain
        or domain.endswith(f".{disposable_domain}")
        for disposable_domain in DISPOSABLE_DOMAINS
    )


def _check_mx_records(domain: str) -> tuple[bool, str]:
    """
    Return MX presence and status.

    NXDOMAIN and an authoritative no-answer are treated as missing.
    Transient resolver failures are treated as unavailable.
    """
    try:
        answers = dns.resolver.resolve(
            domain,
            "MX",
            lifetime=DNS_LOOKUP_TIMEOUT_SECONDS,
        )
        if answers:
            return True, "present"
        return False, "missing"

    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return False, "missing"

    except Exception:
        # Do not expose resolver details or mistake an outage for
        # confirmed evidence that the domain has no mail exchanger.
        return False, "unavailable"


def analyze_email(email: str) -> dict:
    result = {
        "valid_format": False,
        "domain": "",
        "mx_records": False,
        "mx_status": "not_checked",
        "disposable": False,
        "risk_flag": "high",
    }

    if not isinstance(email, str) or not email.strip():
        return result

    try:
        validated = validate_email(
            email.strip(),
            check_deliverability=False,
            allow_smtputf8=False,
        )
    except EmailNotValidError:
        return result

    result["valid_format"] = True
    domain = validated.ascii_domain.lower()
    result["domain"] = domain

    disposable = _is_disposable_domain(domain)
    result["disposable"] = disposable

    mx_records, mx_status = _check_mx_records(domain)
    result["mx_records"] = mx_records
    result["mx_status"] = mx_status

    if disposable:
        result["risk_flag"] = "high"
    elif mx_status == "missing":
        result["risk_flag"] = "medium"
    else:
        # An unavailable lookup is unknown evidence, not a confirmed
        # domain failure. Risk scoring will use mx_status explicitly.
        result["risk_flag"] = "low"

    return result
