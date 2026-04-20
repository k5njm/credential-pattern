"""File discovery and secret extraction."""

import re
from pathlib import Path

from .heuristics import score_finding
from .models import SecretFinding

DISPLAY_THRESHOLD = 0.4

# Matches: export VAR=value, export VAR="value", export VAR='value'
EXPORT_RE = re.compile(
    r"""^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)=(?:"([^"]*)"|'([^']*)'|(\S+))"""
)

# Matches: VAR=value, VAR="value", VAR='value' (no export)
ENV_RE = re.compile(
    r"""^([A-Za-z_][A-Za-z0-9_]*)=(?:"([^"]*)"|'([^']*)'|(.+))"""
)


def discover_files() -> list[str]:
    """Find files to scan for secrets."""
    home = Path.home()
    targets = []

    # ~/.zshrc
    zshrc = home / ".zshrc"
    if zshrc.exists():
        targets.append(str(zshrc))

    # ~/.bashrc
    bashrc = home / ".bashrc"
    if bashrc.exists():
        targets.append(str(bashrc))

    # ~/.env
    home_env = home / ".env"
    if home_env.exists():
        targets.append(str(home_env))

    # ~/bin/.env
    bin_env = home / "bin" / ".env"
    if bin_env.exists():
        targets.append(str(bin_env))

    # ~/repos/**/.env (max depth 4)
    repos = home / "repos"
    if repos.exists():
        for env_file in repos.glob("**/.env"):
            relative = env_file.relative_to(repos)
            if len(relative.parts) <= 4:
                targets.append(str(env_file))

    return sorted(set(targets))


def parse_lines(path: str) -> list[tuple[int, str, str]]:
    """Extract (line_number, var_name, value) from a file.

    For .zshrc/.bashrc: only export lines.
    For .env files: all VAR=VALUE lines.
    """
    results = []
    is_shell_rc = path.endswith((".zshrc", ".bashrc", ".bash_profile", ".profile"))

    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, start=1):
                line = line.rstrip("\n")

                # Skip comments
                stripped = line.strip()
                if stripped.startswith("#") or not stripped:
                    continue

                if is_shell_rc:
                    m = EXPORT_RE.match(line)
                    if m:
                        name = m.group(1)
                        value = m.group(2) or m.group(3) or m.group(4) or ""
                        results.append((i, name, value))
                else:
                    m = ENV_RE.match(stripped)
                    if m:
                        name = m.group(1)
                        value = m.group(2) or m.group(3) or m.group(4) or ""
                        results.append((i, name, value))
    except (OSError, PermissionError):
        pass

    return results


def scan_all() -> list[SecretFinding]:
    """Discover files, parse them, score each variable, return findings above threshold."""
    findings = []

    for path in discover_files():
        for line_number, var_name, value in parse_lines(path):
            if not value:
                continue
            confidence, reason = score_finding(var_name, value)
            if confidence >= DISPLAY_THRESHOLD:
                finding = SecretFinding(
                    source_file=path,
                    line_number=line_number,
                    variable_name=var_name,
                    raw_value=value,
                    confidence=confidence,
                    reason=reason,
                    selected=confidence >= 0.7,
                    op_item_name=var_name.lower(),
                )
                findings.append(finding)

    # Sort by confidence descending, then by file/line
    findings.sort(key=lambda f: (-f.confidence, f.source_file, f.line_number))
    return findings
