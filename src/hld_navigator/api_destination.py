"""Explicit token destinations for local UI and configured HTTPS deployments."""

import os
from urllib.parse import urlsplit


def validate_api_destination(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or "\\" in url
    ):
        raise ValueError("Invalid API URL; credentials, query and fragment are forbidden")
    # Accessing port also validates malformed/out-of-range port values.
    origin = (
        parsed.scheme,
        parsed.hostname.lower(),
        parsed.port or (443 if parsed.scheme == "https" else 80),
    )
    if parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        return url.rstrip("/")
    allowed = os.getenv("HLD_NAVIGATOR_ALLOWED_API_ORIGINS", "").split(",")
    for entry in allowed:
        target = urlsplit(entry.strip())
        if target.scheme == "https" and target.hostname and not target.username:
            if origin == (target.scheme, target.hostname.lower(), target.port or 443):
                return url.rstrip("/")
    raise ValueError("API must use loopback or a configured HTTPS origin")
