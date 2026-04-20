# Setting up CLI tool aliases with `cli:` tags

## How it works

When you tag a 1Password item with `cli:<toolname>`, `api update` generates:

```bash
alias <toolname>='op run -- <toolname>'
```

When you run the aliased command, `op run` resolves all `op://` env vars in the current environment and injects the real secret values into the subprocess — without ever writing them to disk.

## Example: Setting up `bee` CLI

1. **Store the credential:**
   ```bash
   api set bee_api_key "sk-your-key-here"
   ```

2. **Add the `cli:bee` tag in 1Password:**
   - Open 1Password → find "bee_api_key"
   - Add tag: `cli:bee`
   - (Or via CLI: `op item edit bee_api_key --tags cli:bee`)

3. **Regenerate secrets file:**
   ```bash
   api update
   source ~/.zshrc_op_secrets
   ```

4. **Use it:**
   ```bash
   bee              # runs: op run -- bee
                    # bee sees BEE_API_KEY resolved in its environment
   ```

## Multiple credentials for one tool

If a tool needs multiple env vars, tag all relevant items with the same `cli:` tag. `op run` resolves ALL `op://` references in the environment, so the tool will see all of them.

Example: a tool that needs both an API key and a webhook URL:
- Item "mytool_api_key" → tag `cli:mytool`
- Item "mytool_webhook_url" → tag `cli:mytool`

Both get resolved when you run `mytool`.

## How env var names are determined

The env var name is the **item title** in 1Password. Name your items to match what the tool expects:

| Tool expects | Item title in 1Password |
|---|---|
| `BEE_API_KEY` | `bee_api_key` (or `BEE_API_KEY`) |
| `OPENROUTER_API_KEY` | `openrouter_api_key` |

Note: `op run` matches env var names case-insensitively against item references.

## Checking what will be generated

```bash
# Preview without writing
op items list --vault=Personal --categories "API Credential" --format json | \
  jq -r '[.[] | .tags[]? | select(startswith("cli:")) | ltrimstr("cli:")] | unique[]'
```
