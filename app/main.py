from fastapi import FastAPI, Request, BackgroundTasks
import json

from .webhook import verify_signature
from .github import (
    get_installation_token,
    post_pr_review,
    post_inline_comment,
    create_check_run,
)
from .reviewer import run_review
from .redis_store import (
    already_reviewed,
    mark_reviewed,
    allow_review,
    get_repo_mode,
)

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks):
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

    # 🔒 Rate limit per repo
    if not allow_review(repo_full):
        return {"status": "rate_limited"}

    # 🔁 Persistent dedupe
    if already_reviewed(pr_number, commit_sha):
        return {"status": "duplicate"}

    mark_reviewed(pr_number, commit_sha)

    background.add_task(process_review, payload)
    return {"status": "accepted"}


def process_review(payload: dict):
    pr = payload["pull_request"]
    pr_number = pr["number"]
    commit_sha = pr["head"]["sha"]
    repo_full = payload["repository"]["full_name"]
    owner, repo = repo_full.split("/")

    try:
        token = get_installation_token(payload["installation"]["id"])

        mode = get_repo_mode(repo_full)  # strict | relaxed
        review = run_review(payload, token)

        if not review:
            return

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

        # Inline comments only in strict mode
        if mode == "strict":
            for line in review.splitlines():
                if line.startswith("[HIGH]") and ".py" in line:
                    filename = line.split()[1]
                    post_inline_comment(
                        owner,
                        repo,
                        pr_number,
                        token,
                        line,
                        commit_sha,
                        filename,
                        position=1,
                    )

        post_pr_review(
            owner,
            repo,
            pr_number,
            token,
            f"""
🤖 **AI Code Review (v3)**

Mode: `{mode}`

{review}

---
Async • Rate-limited • Persistent
""",
        )

    except Exception as e:
        print("V3 ERROR:", e)

@app.get("/health")
def health():
    return {"status": "ok"}
