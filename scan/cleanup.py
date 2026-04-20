"""File backup and line replacement."""

import shutil
from pathlib import Path

from .models import SecretFinding


def backup_file(path: str) -> str:
    """Create a backup of the file. Returns the backup path."""
    p = Path(path)
    backup = p.with_suffix(p.suffix + ".bak")
    # Don't overwrite existing backups
    counter = 1
    while backup.exists():
        backup = p.with_suffix(f"{p.suffix}.bak.{counter}")
        counter += 1
    shutil.copy2(path, backup)
    return str(backup)


def replace_with_opref(
    path: str,
    line_number: int,
    var_name: str,
    op_item_name: str,
    vault: str = "Personal",
) -> None:
    """Replace a line with an op:// reference."""
    ref = f'op://{vault}/{op_item_name}/credential'
    is_shell_rc = path.endswith((".zshrc", ".bashrc", ".bash_profile", ".profile"))

    if is_shell_rc:
        new_line = f'export {var_name}="{ref}"'
    else:
        new_line = f"{var_name}={ref}"

    _replace_line(path, line_number, new_line)


def remove_line(path: str, line_number: int) -> None:
    """Remove a line from the file (replaces with empty line to preserve numbering context)."""
    _replace_line(path, line_number, "")


def _replace_line(path: str, line_number: int, new_content: str) -> None:
    """Replace a specific line in a file."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    idx = line_number - 1
    if 0 <= idx < len(lines):
        # Preserve trailing newline
        lines[idx] = new_content + "\n" if new_content else "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def apply_cleanups(findings: list[SecretFinding], vault: str = "Personal") -> list[str]:
    """Apply all file cleanups for selected findings. Returns list of log messages.

    Processes in reverse line-number order per file to preserve line numbers.
    """
    messages = []

    # Group by file
    by_file: dict[str, list[SecretFinding]] = {}
    for f in findings:
        if f.selected:
            by_file.setdefault(f.source_file, []).append(f)

    for path, file_findings in by_file.items():
        # Backup first
        backup_path = backup_file(path)
        messages.append(f"Backed up {path} → {backup_path}")

        # Process in reverse line order
        for finding in sorted(file_findings, key=lambda f: -f.line_number):
            if finding.replacement == "remove":
                remove_line(path, finding.line_number)
                messages.append(
                    f"Removed line {finding.line_number} ({finding.variable_name}) from {finding.short_path}"
                )
            else:
                replace_with_opref(
                    path,
                    finding.line_number,
                    finding.variable_name,
                    finding.op_item_name,
                    vault,
                )
                messages.append(
                    f"Replaced {finding.variable_name} with op:// ref at {finding.short_path}:{finding.line_number}"
                )

    return messages
