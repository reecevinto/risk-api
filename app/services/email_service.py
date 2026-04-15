import re
import dns.resolver

DISPOSABLE_DOMAINS = {
    "mailinator.com",
    "10minutemail.com",
    "tempmail.com",
    "guerrillamail.com"
}


def analyze_email(email: str):
    result = {
        "valid_format": False,
        "domain": "",
        "mx_records": False,
        "disposable": False,
        "risk_flag": "low"
    }

    # 1. Validate format
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, email):
        result["risk_flag"] = "high"
        return result

    result["valid_format"] = True

    # 2. Extract domain (normalize)
    domain = email.split("@")[1].lower()
    result["domain"] = domain

    # 3. Check disposable
    if domain in DISPOSABLE_DOMAINS:
        result["disposable"] = True

    # 4. Check MX records
    try:
        answers = dns.resolver.resolve(domain, "MX")
        if answers:
            result["mx_records"] = True

    except dns.resolver.NoAnswer:
        result["mx_records"] = False

    except dns.resolver.NXDOMAIN:
        result["mx_records"] = False

    except Exception:
        result["mx_records"] = False

    # 5. Risk scoring
    if result["disposable"]:
        result["risk_flag"] = "high"
    elif not result["mx_records"]:
        result["risk_flag"] = "medium"
    else:
        result["risk_flag"] = "low"

    return result