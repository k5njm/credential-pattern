# credential-pattern

A portable shell pattern for managing API credentials and CLI tool secrets using [1Password CLI](https://developer.1password.com/docs/cli/).

## How it works

```
┌─────────────────────────────────────────────────────────────────┐
│  1Password Vault (Personal)                                     │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │ Category:            │  │ Tags:                 │            │
│  │   "API Credential"   │  │   cli:bee             │            │
│  │ Field: credential    │  │   cli:calvibe         │            │
│  └──────────────────────┘  └──────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
        │                           │
        ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  `api update` generates ~/.zshrc_op_secrets                     │
│                                                                 │
│  export bee_api_key="op://Personal/bee_api_key/credential"      │
│  alias bee='op run -- bee'                                      │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Shell sources the file → env vars are op:// references         │
│  `op run` resolves them at invocation time                      │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- [1Password CLI](https://developer.1password.com/docs/cli/get-started/) (`op`) installed and signed in
- 1Password desktop app with CLI integration enabled (for biometric unlock)
- zsh (bash compatible with minor tweaks)

## Quick start

```bash
# Clone and source
git clone git@github.com:k5njm/credential-pattern.git ~/.credential-pattern
echo 'source ~/.credential-pattern/api.zsh' >> ~/.zshrc
source ~/.zshrc

# Add your first credential
api set my_api_key sk-abc123

# Tag it for CLI use (in 1Password, add tag "cli:mytool")
# Then regenerate the secrets file
api update

# Use it
op run -- mytool  # mytool sees MY_API_KEY in its env
```

## Commands

| Command | Description |
|---|---|
| `api` | List all API Credential items |
| `api get <name> [field]` | Read a credential (default field: `credential`) |
| `api set <name> <value>` | Create or update an API Credential item |
| `api del <name>` | Delete a credential (with confirmation) |
| `api update` | Regenerate `~/.zshrc_op_secrets` from vault |
| `api token <vault> [hours]` | Generate a scoped service account token |

## Concepts

### API Credential category

All managed credentials use the 1Password category "API Credential" with a field named `credential`. This convention makes `api update` possible — it queries all items of this category to build the secrets file.

### Secret references as env vars

The generated `~/.zshrc_op_secrets` exports env vars with `op://` URI values:

```bash
export openrouter_api_key="op://Personal/openrouter_api_key/credential"
```

These are **not** resolved at shell startup. They're resolved lazily when you run a command via `op run -- <cmd>`, which injects the real values into that process's environment.

### CLI tool aliases via tags

Add a `cli:<toolname>` tag to any 1Password item. `api update` generates:

```bash
alias <toolname>='op run -- <toolname>'
```

This means the tool automatically gets all matching env vars injected without ever writing secrets to disk.

### Service account tokens for automation

For non-interactive contexts (CI, AI agents, cron), generate a short-lived service account token scoped to a specific vault:

```bash
# Generate an 8-hour token for the home-network vault (read-only)
api token home-network 8

# Use it in automation
export OP_SERVICE_ACCOUNT_TOKEN="ops_..."
op read "op://home-network/some_item/credential"
```

The token is scoped to a single vault with read-only access and expires automatically.

## File layout

```
~/.credential-pattern/
├── api.zsh              # The api() function — source this
├── install.sh           # Optional: adds source line + runs first update
├── README.md            # This file
└── examples/
    ├── op-run-tags.md   # How to set up cli: tags
    └── service-tokens.md # Automation patterns with scoped tokens
```

## Portability

This pattern works on any machine with `op` CLI installed. To bring it to a new machine:

1. Install 1Password CLI and sign in
2. Clone this repo
3. Source `api.zsh` in your shell rc
4. Run `api update`

Your credentials live in 1Password — the local machine only ever sees `op://` references and short-lived resolved values in process memory.
