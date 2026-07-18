"""
User-Agent parsing — pure regex, no external dependencies.

Returns a dict with keys: browser_name, browser_version, os_name,
os_version, device_type.
"""

import re

# ── Browser detection (priority order) ────────────────────

_BROWSER_RULES: list[tuple[str, str, type[re.Pattern]]] = [
    # (name, version_group, pattern)
    # Order matters — first match wins
    ("Edge", "Edg", re.compile(r"Edg[E]?/([\d.]+)")),
    ("Opera", "OPR", re.compile(r"(?:OPR|Opera)[ /]([\d.]+)")),
    ("Chrome", "Chrome", re.compile(r"Chrome/([\d.]+)")),
    ("Firefox", "Firefox", re.compile(r"Firefox/([\d.]+)")),
    ("Firefox", "FxiOS", re.compile(r"FxiOS/([\d.]+)")),
    ("Safari", "Version", re.compile(r"Version/([\d.]+).*Safari/")),
    ("IE", "MSIE", re.compile(r"MSIE ([\d.]+)")),
    ("IE", "Trident", re.compile(r"rv:([\d.]+).*Trident/")),
]


def _detect_browser(ua: str) -> tuple[str, str]:
    """Return (browser_name, browser_version)."""
    for name, version_key, pattern in _BROWSER_RULES:
        m = pattern.search(ua)
        if m:
            return name, m.group(1)
    return "Unknown", ""


# ── OS detection (priority order) ─────────────────────────

_OS_RULES: list[tuple[str, type[re.Pattern]]] = [
    ("Windows", re.compile(r"Windows NT ([\d.]+)")),
    ("macOS", re.compile(r"Mac OS X ([\d_]+)")),
    ("iOS", re.compile(r"(?:iPhone|iPad).*? OS ([\d_]+)")),
    ("Android", re.compile(r"Android ([\d.]+)")),
    ("Chrome OS", re.compile(r"CrOS|Chromebook")),
    ("Linux", re.compile(r"Linux")),
]


def _detect_os(ua: str) -> tuple[str, str]:
    """Return (os_name, os_version)."""
    for name, pattern in _OS_RULES:
        m = pattern.search(ua)
        if m:
            version = m.group(1).replace("_", ".") if m.lastindex else ""
            return name, version
    return "Unknown", ""


# ── Device type detection ─────────────────────────────────

_DEVICE_RULES: list[tuple[str, str, str]] = [
    # (type, keyword_1, keyword_2)
    ("tablet", "iPad", ""),
    ("tablet", "Tablet", "Android"),
    ("mobile", "Mobile", ""),
    ("mobile", "Android", ""),
]


def _detect_device(ua: str) -> str:
    """Return 'desktop', 'tablet', or 'mobile'."""
    for dtype, kw1, kw2 in _DEVICE_RULES:
        if kw1 in ua and (not kw2 or kw2 in ua):
            return dtype
    return "desktop"


# ── Public API ────────────────────────────────────────────


def parse_user_agent(ua_string: str | None) -> dict:
    """
    Parse a User-Agent string into structured data.

    Returns:
        dict with keys: browser_name, browser_version, os_name,
                        os_version, device_type
    """
    if not ua_string or not ua_string.strip():
        return {
            "browser_name": None,
            "browser_version": None,
            "os_name": None,
            "os_version": None,
            "device_type": None,
        }

    ua = ua_string.strip()
    browser_name, browser_version = _detect_browser(ua)

    # Fix: Safari version is in "Version/..." not "Safari/..."
    if browser_name == "Safari" and not browser_version:
        m = re.search(r"Version/([\d.]+)", ua)
        browser_version = m.group(1) if m else ""

    os_name, os_version = _detect_os(ua)
    device_type = _detect_device(ua)

    return {
        "browser_name": browser_name,
        "browser_version": browser_version or None,
        "os_name": os_name,
        "os_version": os_version or None,
        "device_type": device_type,
    }
