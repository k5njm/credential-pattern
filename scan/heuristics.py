"""Secret detection heuristics — scoring logic for variable name/value pairs."""

import math
import re

# Variable names that strongly suggest secrets
SECRET_NAME_PATTERNS = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|credential|auth[_-]?token|"
    r"private[_-]?key|app[_-]?password|passphrase)"
)

# Variable names that are almost never secrets
NON_SECRET_NAMES = re.compile(
    r"(?i)^(HOME|PATH|DIR|DIRECTORY|EDITOR|LANG|LANGUAGE|SHELL|MODEL|"
    r"VERSION|HOST|HOSTNAME|PORT|URL|SERVER|BASE|PROFILE|THEME|TERM|"
    r"USER|NAME|EMAIL|DISPLAY|BROWSER|PAGER|ZSH|OSTYPE|TMPDIR|XDG_)$"
)

# Known API key prefixes
SECRET_PREFIXES = (
    "sk-", "sk-proj-", "fmu1-", "AIza", "ghp_", "gho_", "ghs_", "ghu_",
    "glpat-", "xoxb-", "xoxp-", "xoxs-", "SG.", "key-", "rk-", "whsec_",
    "pk_live_", "sk_live_", "sk_test_", "pk_test_", "sk-or-", "eyJ",
    "AKIA",  # AWS access key
)

# Values that are clearly not secrets
NON_SECRET_VALUES = re.compile(
    r"^(true|false|yes|no|on|off|0|1|none|null|"
    r"gpt-4|gpt-3\.5|claude|minimax|gemini|llama|"
    r"\d+(\.\d+)*|"  # version numbers
    r"[a-z][a-z0-9]*(/[a-z][a-z0-9_-]*)*(:[a-z0-9_.-]+)?$)"  # model identifiers like "org/model:tag"
, re.IGNORECASE)


def compute_entropy(value: str) -> float:
    """Shannon entropy of a string. Higher = more random."""
    if not value:
        return 0.0
    freq = {}
    for c in value:
        freq[c] = freq.get(c, 0) + 1
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def is_hex_string(value: str) -> bool:
    """Check if value is a long hex string."""
    return bool(re.match(r"^[0-9a-fA-F]{32,}$", value))


def is_base64_like(value: str) -> bool:
    """Check if value looks like a base64 token (20+ chars, mixed case/digits)."""
    if len(value) < 20:
        return False
    if not re.match(r"^[A-Za-z0-9+/=_-]+$", value):
        return False
    has_upper = any(c.isupper() for c in value)
    has_lower = any(c.islower() for c in value)
    has_digit = any(c.isdigit() for c in value)
    return sum([has_upper, has_lower, has_digit]) >= 2


def score_finding(name: str, value: str) -> tuple[float, str]:
    """Score a name/value pair. Returns (confidence, reason)."""
    # Immediate exclusions
    if value.startswith("op://"):
        return 0.0, "already managed"
    if value.startswith(("/", "~/", "./", "$HOME", "${")):
        return 0.0, "file path"
    if re.match(r"^https?://[^:@]*$", value):
        return 0.0, "URL without credentials"
    if NON_SECRET_VALUES.match(value):
        return 0.0, "non-secret value"

    score = 0.0
    reasons = []

    # Name-based signals
    if SECRET_NAME_PATTERNS.search(name):
        score += 0.5
        reasons.append("name pattern")
    elif NON_SECRET_NAMES.match(name):
        score -= 0.4
        reasons.append("non-secret name")

    # Value prefix signals
    for prefix in SECRET_PREFIXES:
        if value.startswith(prefix):
            score += 0.4
            reasons.append(f"prefix: {prefix}")
            break

    # Structural signals
    if is_hex_string(value):
        score += 0.3
        reasons.append("hex string")
    elif is_base64_like(value):
        score += 0.25
        reasons.append("base64-like")

    # Entropy signal
    entropy = compute_entropy(value)
    if entropy > 4.0 and len(value) > 16:
        score += 0.2
        reasons.append(f"high entropy ({entropy:.1f})")

    # Length signal
    if len(value) >= 32:
        score += 0.1
        reasons.append("long value")
    elif len(value) < 8 and score < 0.5:
        score -= 0.3
        reasons.append("short value")

    # URL with embedded credentials
    if re.match(r"https?://[^:]+:[^@]+@", value):
        score += 0.5
        reasons.append("URL with credentials")

    confidence = max(0.0, min(1.0, score))
    reason = ", ".join(reasons) if reasons else "heuristic"
    return confidence, reason
