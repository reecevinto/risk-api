import math
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

# Day 10 - IPinfo network intelligence
IPINFO_TOKEN = os.getenv("IPINFO_TOKEN")


def _load_positive_timeout() -> float:
    raw_timeout = os.getenv("IPINFO_TIMEOUT_SECONDS", "3.0")

    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "IPINFO_TIMEOUT_SECONDS must be a finite positive number"
        ) from exc

    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(
            "IPINFO_TIMEOUT_SECONDS must be a finite positive number"
        )

    return timeout


IPINFO_TIMEOUT_SECONDS = _load_positive_timeout()
