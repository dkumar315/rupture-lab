import re
from urllib.parse import unquote

_INVALID_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_CONTROL_NAMESPACE = "/_rupturelab"


def local_request_path(target: str) -> str:
    """Return a validated, decoded local path for an HTTP request target."""
    if len(target) == 0 or len(target) > 2048:
        raise ValueError("path must contain between 1 and 2048 characters")

    if not target.startswith("/") or target.startswith("//"):
        raise ValueError("path must be a local request target starting with a single '/'")

    if "#" in target:
        raise ValueError("path must not contain a URL fragment")

    raw_path = target.partition("?")[0]

    if "\\" in raw_path or _INVALID_PERCENT_ESCAPE.search(raw_path):
        raise ValueError("path contains an invalid or ambiguous escape")

    try:
        decoded_path = unquote(raw_path, errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("path contains invalid UTF-8 escaping") from exc

    if decoded_path.startswith("//") or "\\" in decoded_path:
        raise ValueError("path must not contain an authority-like path")

    if "?" in decoded_path or "#" in decoded_path:
        raise ValueError("path contains an encoded URL delimiter")

    if any(ord(character) < 32 or ord(character) == 127 for character in decoded_path):
        raise ValueError("path must not contain control characters")

    if any(segment in {".", ".."} for segment in decoded_path.split("/")):
        raise ValueError("path must not contain dot segments")

    if decoded_path == _CONTROL_NAMESPACE or decoded_path.startswith(f"{_CONTROL_NAMESPACE}/"):
        raise ValueError("Experiments cannot target the RuptureLab control namespace")

    return decoded_path
