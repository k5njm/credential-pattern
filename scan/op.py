"""1Password CLI wrapper."""

import os
import subprocess


def get_vault() -> str:
    return os.environ.get("CREDENTIAL_PATTERN_VAULT", "Personal")


def check_auth() -> bool:
    """Check if op CLI is authenticated."""
    result = subprocess.run(
        ["op", "whoami"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def item_exists(name: str, vault: str | None = None) -> bool:
    """Check if an item already exists in the vault."""
    vault = vault or get_vault()
    result = subprocess.run(
        ["op", "item", "get", name, f"--vault={vault}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def create_credential(name: str, value: str, vault: str | None = None) -> tuple[bool, str]:
    """Create an API Credential item. Returns (success, message)."""
    vault = vault or get_vault()

    if item_exists(name, vault):
        result = subprocess.run(
            ["op", "item", "edit", name, f"--vault={vault}", f"credential={value}"],
            capture_output=True,
            text=True,
        )
        action = "Updated"
    else:
        result = subprocess.run(
            [
                "op", "item", "create",
                "--category=API Credential",
                f"--title={name}",
                f"--vault={vault}",
                f"credential={value}",
            ],
            capture_output=True,
            text=True,
        )
        action = "Created"

    if result.returncode == 0:
        return True, f"{action} '{name}' in vault '{vault}'"
    return False, f"Failed to create '{name}': {result.stderr.strip()}"


def add_tags(name: str, tags: list[str], vault: str | None = None) -> tuple[bool, str]:
    """Add tags to an item. Returns (success, message)."""
    vault = vault or get_vault()
    if not tags:
        return True, "No tags to add"

    tag_str = ",".join(tags)
    result = subprocess.run(
        ["op", "item", "edit", name, f"--vault={vault}", f"--tags={tag_str}"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, f"Tagged '{name}' with {tag_str}"
    return False, f"Failed to tag '{name}': {result.stderr.strip()}"
