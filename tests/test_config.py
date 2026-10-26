import math

import pytest

from app.core.config import _load_positive_timeout


@pytest.mark.parametrize(
    ("raw_timeout", "expected"),
    [
        (None, 3.0),
        ("3.0", 3.0),
        ("0.5", 0.5),
        ("10", 10.0),
    ],
)
def test_load_positive_timeout_accepts_valid_values(
    monkeypatch,
    raw_timeout,
    expected,
):
    if raw_timeout is None:
        monkeypatch.delenv(
            "IPINFO_TIMEOUT_SECONDS",
            raising=False,
        )
    else:
        monkeypatch.setenv(
            "IPINFO_TIMEOUT_SECONDS",
            raw_timeout,
        )

    assert _load_positive_timeout() == expected


@pytest.mark.parametrize(
    "raw_timeout",
    [
        "invalid",
        "",
        "NaN",
        "Infinity",
        "-Infinity",
        "0",
        "-1",
    ],
)
def test_load_positive_timeout_rejects_invalid_values(
    monkeypatch,
    raw_timeout,
):
    monkeypatch.setenv(
        "IPINFO_TIMEOUT_SECONDS",
        raw_timeout,
    )

    with pytest.raises(
        ValueError,
        match="IPINFO_TIMEOUT_SECONDS must be a finite positive number",
    ):
        _load_positive_timeout()
