# Service Account Tokens for Automation

## Overview

For non-interactive contexts — AI agents, cron jobs, CI pipelines — you can't rely on biometric unlock. Instead, generate a **short-lived, vault-scoped service account token**.

## Generating a token

```bash
# Interactive: generates token and prints export command
api token home-network 8    # 8-hour expiry, read-only on home-network vault

# Capture it programmatically
export OP_SERVICE_ACCOUNT_TOKEN=$(api token home-network 8)
```

## Properties of service account tokens

- **Scoped to one vault** — can only read items from the specified vault
- **Read-only** — cannot create, edit, or delete items
- **Time-limited** — expires automatically (default 8 hours)
- **No biometric required** — works in headless environments
- **Prefix**: `ops_...`

## Usage patterns

### AI agent session bootstrap

```bash
# Agent asks user for permission, then:
export OP_SERVICE_ACCOUNT_TOKEN=$(api token home-network 8)

# Now the agent can read credentials without further prompts
op read "op://home-network/hass_token/credential"
op read "op://home-network/opnsense_api_key/credential"
```

### SSH agent with vault-scoped key

```bash
# Load an SSH key from a specific vault using a service token
SOCKET=/tmp/automation-ssh.sock
rm -f $SOCKET
ssh-agent -a $SOCKET

OP_SERVICE_ACCOUNT_TOKEN="$token" \
  op read "op://home-network/ssh_key/private key?ssh-format=openssh" \
  | SSH_AUTH_SOCK=$SOCKET ssh-add -

# Use the dedicated socket
export SSH_AUTH_SOCK=$SOCKET
ssh myhost "uptime"
```

### CI/CD pipeline

```yaml
# GitHub Actions example — store a long-lived service account token as a secret
# (or better: generate one in a setup step with a short expiry)
env:
  OP_SERVICE_ACCOUNT_TOKEN: ${{ secrets.OP_SERVICE_ACCOUNT_TOKEN }}

steps:
  - run: |
      API_KEY=$(op read "op://CI/deploy_key/credential")
      deploy --key "$API_KEY"
```

### Cron job

```bash
# In crontab or systemd timer — token must be pre-generated or use a
# long-lived service account (create in 1Password admin console)
OP_SERVICE_ACCOUNT_TOKEN="ops_..." op read "op://vault/item/field"
```

## Security considerations

- **Prefer short expiry** — 8h covers a work session; use 1h for CI jobs
- **One token per context** — don't share tokens across agents/jobs
- **Vault isolation** — automation credentials should live in a dedicated vault, not Personal
- **Token rotation** — service account tokens are disposable; generate fresh ones per session
- **Audit trail** — 1Password logs all access by service accounts

## Vault layout recommendation

```
Personal vault        → human credentials, API keys for dev tools
home-network vault    → infrastructure automation (router, cameras, HA)
ci vault              → deploy keys, registry tokens
```

Each vault gets its own scoped tokens. A compromised token for `ci` can't read `home-network` secrets.
