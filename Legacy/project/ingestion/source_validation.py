"""
Validation helpers for official regulator-source URLs.
"""

from __future__ import annotations

from urllib.parse import urlparse


ALLOWED_DOMAINS = {
    "rbi.org.in": {"rbi.org.in", "www.rbi.org.in"},
    "sebi.gov.in": {"sebi.gov.in", "www.sebi.gov.in"},
}

ALLOWED_PATH_HINTS = (
    "/scripts/",
    "/notifications",
    "/notification",
    "/circular",
    "/circulars",
    "/master-circular",
    "/master-circulars",
    "/master-direction",
    "/master-directions",
    "/regulation",
    "/regulations",
    "/legal",
    "/order",
    "/orders",
    ".pdf",
    ".html",
)


def normalize_hostname(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.hostname or "").lower()


def get_regulator_key(source: str | None) -> str | None:
    if not source:
        return None

    normalized = str(source).strip().lower()
    if "rbi" in normalized:
        return "rbi.org.in"
    if "sebi" in normalized:
        return "sebi.gov.in"
    return None


def is_allowed_regulator_url(url: str, source: str | None = None) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False

    hostname = normalize_hostname(url)
    regulator_key = get_regulator_key(source)

    if regulator_key:
        allowed_hosts = ALLOWED_DOMAINS[regulator_key]
    else:
        allowed_hosts = set().union(*ALLOWED_DOMAINS.values())

    if hostname not in allowed_hosts:
        return False

    path = (parsed.path or "").lower()
    if not path:
        return False

    return any(hint in path for hint in ALLOWED_PATH_HINTS)


def validate_regulator_url(url: str, source: str | None = None) -> str:
    if not is_allowed_regulator_url(url, source=source):
        expected = get_regulator_key(source)
        if expected == "rbi.org.in":
            raise ValueError("Only official RBI document URLs are allowed.")
        if expected == "sebi.gov.in":
            raise ValueError("Only official SEBI document URLs are allowed.")
        raise ValueError("Only official regulator document URLs are allowed.")

    return url
