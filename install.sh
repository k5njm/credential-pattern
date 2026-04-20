#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_LINE="source \"$SCRIPT_DIR/api.zsh\""

# Detect shell rc file
if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$SHELL" == */zsh ]]; then
  RC_FILE="${HOME}/.zshrc"
else
  RC_FILE="${HOME}/.bashrc"
fi

echo "credential-pattern installer"
echo "============================"
echo ""

# Check prerequisites
if ! command -v op &>/dev/null; then
  echo "ERROR: 1Password CLI (op) not found." >&2
  echo "Install it: https://developer.1password.com/docs/cli/get-started/" >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq not found." >&2
  echo "Install it: brew install jq / apt install jq" >&2
  exit 1
fi

# Add source line to rc file if not already present
if grep -qF "api.zsh" "$RC_FILE" 2>/dev/null; then
  echo "Already sourced in $RC_FILE — skipping."
else
  echo "" >> "$RC_FILE"
  echo "# 1Password credential pattern" >> "$RC_FILE"
  echo "$SOURCE_LINE" >> "$RC_FILE"
  echo "Added source line to $RC_FILE"
fi

# Source it now for immediate use
source "$SCRIPT_DIR/api.zsh"

echo ""
echo "Done! Run 'api update' to generate your secrets file."
echo "Run 'exec zsh' (or restart your shell) to activate."
