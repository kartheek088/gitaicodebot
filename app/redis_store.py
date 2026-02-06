import os
import time
from redis import Redis

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise RuntimeError("REDIS_URL is not set")

redis = Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_timeout=5,
    retry_on_timeout=True,
)

# ---------- DEDUPE ----------

def already_reviewed(pr_number: int, commit_sha: str) -> bool:
    key = f"reviewed:{pr_number}"
    last_sha = redis.get(key)
    return last_sha == commit_sha


def mark_reviewed(pr_number: int, commit_sha: str):
    key = f"reviewed:{pr_number}"
    # expire after 24h
    redis.set(key, commit_sha, ex=60 * 60 * 24)


# ---------- RATE LIMIT ----------

def allow_review(repo: str, limit: int = 10, window: int = 3600) -> bool:
    """
    Allow at most `limit` reviews per repo per `window` seconds
    """
    key = f"rate:{repo}"
    count = redis.incr(key)

    if count == 1:
        redis.expire(key, window)

    return count <= limit


# ---------- REPO CONFIG ----------

def get_repo_mode(repo: str) -> str:
    """
    strict | relaxed
    """
    return redis.get(f"config:{repo}") or "strict"


def set_repo_mode(repo: str, mode: str):
    redis.set(f"config:{repo}", mode)
