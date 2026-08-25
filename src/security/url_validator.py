"""
Centralized URL security validation for the multi-site job collection prototype.

All URL validation in the application MUST go through validate_url() from this module.
This replaces the old Topjobs-only hostname allowlist in app.py.
"""

import socket
import ipaddress
import urllib.parse
import pathlib
import os


# Load blocked domains list from config file
def _load_domain_list(filename):
    """Loads a newline-separated domain list from config/."""
    config_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "config"
    filepath = config_dir / filename
    if not filepath.exists():
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        return {
            line.strip().lower()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        }


def _is_unsafe_ip(ip_str):
    """Returns True if the IP address is private, loopback, link-local,
    multicast, reserved, unspecified, or the metadata-service address."""
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # If we can't parse it, treat as unsafe

    # Explicit metadata-service check (AWS/GCP/Azure)
    if ip_str in ("169.254.169.254", "fd00:ec2::254"):
        return True

    return (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def validate_url(url):
    """Validates a URL for safe public web requests.

    Returns:
        (is_valid: bool, reason: str)
        When valid, reason is empty string.
        When invalid, reason describes why.

    Checks performed:
        1. Scheme must be http or https
        2. Hostname must be present and non-empty
        3. No embedded credentials (username/password in URL)
        4. Port must be 80, 443, or default (absent)
        5. Not on the blocked domains list
        6. Hostname must resolve to a public internet IP
        7. Not localhost, private, loopback, link-local, multicast,
           reserved, unspecified, or metadata-service IP
        8. Reject dangerous URI schemes (file://, ftp://, data:, javascript:)
    """
    if not isinstance(url, str) or not url.strip():
        return False, "Empty URL"

    url = url.strip()

    # Reject dangerous pseudo-schemes before parsing
    lower_url = url.lower()
    for dangerous in ("file://", "ftp://", "data:", "javascript:", "gopher://"):
        if lower_url.startswith(dangerous):
            return False, f"Dangerous URL scheme: {dangerous}"

    parsed = urllib.parse.urlparse(url)

    # 1. Scheme check
    if parsed.scheme not in ("http", "https"):
        return False, f"Invalid scheme '{parsed.scheme}'. Only http and https are allowed."

    # 2. Hostname check
    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname in URL."

    hostname_lower = hostname.lower()

    # 3. Reject embedded credentials
    if parsed.username or parsed.password:
        return False, "Credentials in URL are strictly prohibited."

    # 4. Port check — only 80, 443, or default (None)
    port = parsed.port
    if port is not None and port not in (80, 443):
        return False, f"Non-standard port {port} is not allowed. Only ports 80 and 443 are accepted."

    # 5. Check blocked domains list
    blocked = _load_domain_list("blocked_domains.txt")
    if hostname_lower in blocked:
        return False, f"Domain '{hostname_lower}' is on the blocked domains list."

    # Also check if any parent domain is blocked (e.g., block "evil.com" blocks "sub.evil.com")
    parts = hostname_lower.split(".")
    for i in range(len(parts) - 1):
        parent = ".".join(parts[i:])
        if parent in blocked:
            return False, f"Domain '{hostname_lower}' is blocked (parent domain '{parent}' is on the blocked list)."

    # 6. Reject well-known unsafe hostnames before DNS
    unsafe_hostnames = {
        "localhost", "localhost.localdomain",
        "127.0.0.1", "0.0.0.0", "::1",
        "169.254.169.254",
        "[::1]",
    }
    if hostname_lower in unsafe_hostnames:
        return False, f"SSRF Protection: hostname '{hostname_lower}' is a local/internal address."

    # Check if hostname is a raw IP address
    try:
        ip_obj = ipaddress.ip_address(hostname_lower.strip("[]"))
        if _is_unsafe_ip(str(ip_obj)):
            return False, f"SSRF Protection: IP address {ip_obj} is private/local/reserved."
        # Valid public IP used directly — allowed
        return True, ""
    except ValueError:
        pass  # Not a raw IP, continue with DNS resolution

    # 7. DNS resolution — verify hostname resolves to public IP
    try:
        ip_str = socket.gethostbyname(hostname_lower)
    except socket.gaierror as e:
        return False, f"DNS resolution failed for '{hostname_lower}': {e}"

    if _is_unsafe_ip(ip_str):
        return False, f"SSRF Protection: hostname '{hostname_lower}' resolves to private/local IP {ip_str}."

    return True, ""


def validate_redirect_url(original_url, redirect_url):
    """Validates a redirect target URL.
    Applies the same checks as validate_url plus ensures the redirect
    is not going to a different unsafe destination.
    """
    is_valid, reason = validate_url(redirect_url)
    if not is_valid:
        return False, f"Redirect target rejected: {reason}"
    return True, ""


def is_approved_domain(hostname):
    """Checks if a hostname is in the approved domains research record.
    This is informational only — not enforced as an allowlist.
    """
    approved = _load_domain_list("approved_domains.txt")
    return hostname.lower() in approved
