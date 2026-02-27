from fastapi import FastAPI, Request, HTTPException
import json

from .webhook import verify_signature
from .github import (
    get_installation_token,
    post_pr_review,
    create_check_run,
)
from .reviewer import run_review
from .database import init_db
from .models import review_exists, save_review

app = FastAPI()


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"status": "AI Code Reviewer V5 running"}


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    await verify_signature(request, body)

    payload = json.loads(body)
    event = request.headers.get("X-GitHub-Event")

    if event != "pull_request":
        return {"status": "ignored"}

    action = payload.get("action")
    if action not in {"opened", "synchronize", "reopened"}:
        return {"status": "ignored"}

    pr = payload["pull_request"]
    pr_number = pr["number"]
    commit_sha = pr["head"]["sha"]
    repo_full = payload["repository"]["full_name"]
    owner, repo = repo_full.split("/")

    # Deduplicate using SQLite
    if review_exists(repo_full, pr_number, commit_sha):
        return {"status": "duplicate"}

    try:
        token = get_installation_token(payload["installation"]["id"])

        # Your reviewer currently takes (payload, token)
        review = run_review(payload, token)

        if not review:
            return {"status": "no_review"}

        has_high = "[HIGH]" in review
        conclusion = "failure" if has_high else "success"

        create_check_run(
            owner,
            repo,
            token,
            commit_sha,
            conclusion,
            "High severity issues found" if has_high else "No critical issues found",
        )

        post_pr_review(
            owner,
            repo,
            pr_number,
            token,
            f"""
🤖 **AI Code Review (v5)**

{review}

---
Stable • SQLite-backed • No external cache
""",
        )

        save_review(repo_full, pr_number, commit_sha, "completed")

    except Exception as e:
        print("V5 ERROR:", e)
        raise HTTPException(status_code=500, detail="Review failed")

    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}