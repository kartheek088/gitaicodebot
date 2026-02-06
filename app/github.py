import jwt
import time
import requests
from .config import GITHUB_APP_ID, GITHUB_PRIVATE_KEY_PATH

GITHUB_API = "https://api.github.com"


def generate_jwt():
    with open(GITHUB_PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()

    now = int(time.time())
    payload = {
        "iat": now - 30,
        "exp": now + 540,
        "iss": GITHUB_APP_ID,
    }

    return jwt.encode(payload, private_key, algorithm="RS256")


def get_installation_token(installation_id: int) -> str:
    jwt_token = generate_jwt()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    url = f"{GITHUB_API}/app/installations/{installation_id}/access_tokens"
    res = requests.post(url, headers=headers)

    data = res.json()
    if res.status_code != 201 or "token" not in data:
        raise Exception(f"Failed to get installation token: {data}")

    return data["token"]


def github_get(url: str, token: str):
    res = requests.get(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    return res.json()


# -------- V2 ADDITIONS --------

def post_pr_review(owner, repo, pr_number, token, body):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"

    payload = {
        "body": body,
        "event": "COMMENT",
    }

    res = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        },
    )

    if res.status_code not in (200, 201):
        raise Exception(f"PR review failed: {res.text}")


def post_inline_comment(owner, repo, pr_number, token, body, commit_sha, path, position):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/comments"

    payload = {
        "body": body,
        "commit_id": commit_sha,
        "path": path,
        "position": position,
    }

    res = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        },
    )

    if res.status_code != 201:
        raise Exception(f"Inline comment failed: {res.text}")


def create_check_run(owner, repo, token, head_sha, conclusion, summary):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/check-runs"

    payload = {
        "name": "AI Code Review",
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": conclusion,  # success | failure
        "output": {
            "title": "AI Code Review",
            "summary": summary,
        },
    }

    res = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        },
    )

    if res.status_code != 201:
        raise Exception(f"Check run failed: {res.text}")
