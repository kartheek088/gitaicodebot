# gitaicodebot

A GitHub App that reviews pull requests. When a PR is opened or updated, it:

1. Verifies the webhook's `X-Hub-Signature-256` HMAC (constant-time compare).
2. Skips commits it has already reviewed (SQLite, keyed on repo + PR + head SHA).
3. Authenticates as the App (RS256 JWT → installation access token).
4. Fetches the PR's file patches and runs a secret check: known key patterns (AWS, Google, OpenAI-style, private-key headers) plus a Shannon-entropy check per line.
5. Masks known key prefixes, then sends the diff to an LLM (Groq) with a prompt asking for `[HIGH]` / `[MEDIUM]` / `[LOW]` findings.
6. Posts the result as a PR review and creates a check run — **failure** if anything `[HIGH]` was found, otherwise **success**.

Example output: the reviews on [cerd_scanner#1](https://github.com/kartheek088/cerd_scanner/pull/1).

## Structure

```
app/
  main.py      FastAPI app: /webhook, /health
  webhook.py   HMAC signature verification
  github.py    App JWT, installation token, reviews, check runs
  reviewer.py  builds the diff, runs the secret check, masks, calls the LLM
  secrets.py   regex + entropy secret detection
  llm.py       Groq client and review prompt
  database.py  SQLite schema (installations, reviews)
  models.py    review dedupe helpers
```

## Running it

Requires Python 3.11 and a GitHub App with **Pull requests: read & write** and **Checks: read & write**, subscribed to `pull_request` events.

```bash
pip install -r requirements.txt
export GITHUB_APP_ID=...            # from the App settings page
export GITHUB_PRIVATE_KEY_PATH=...  # path to the App's .pem
export GITHUB_WEBHOOK_SECRET=...
export GROQ_API_KEY=...
uvicorn app.main:app --port 8000
```

Point the App's webhook URL at `https://<your-host>/webhook` (for local testing, a tunnel such as `ngrok` or `cloudflared`).

## Known limitations

- **Masking only replaces the key prefix** (e.g. `sk-` → `[REDACTED]`); the rest of the key is still sent to the LLM. Secrets should be masked by their full matched span.
- The entropy check runs on whole diff lines, so minified code and long hashes produce false positives.
- The OpenAI pattern (`sk-` + 48 chars) misses newer key formats such as `sk-proj-…`.
- Only the first page of changed files is fetched (GitHub returns 30 by default), so very large PRs are partially reviewed.
- The LLM's severity labels decide the check result, so a hallucinated `[HIGH]` fails the check.
- No automated tests yet.
- `REDIS_URL` is still read in `config.py` but unused since V5 moved to SQLite.

## History

V1 → V5 iterated on the same webhook: Redis-backed dedupe was replaced by SQLite in V5 to remove an external dependency.
