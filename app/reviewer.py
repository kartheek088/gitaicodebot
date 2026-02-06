from .github import github_get
from .llm import review_code
from .secrets import scan_for_secrets


def mask_secrets(text: str) -> str:
    """
    Very conservative masking.
    Enough to prevent leaking secrets to LLM,
    without destroying code structure.
    """
    replacements = [
        "sk-",
        "AKIA",
        "AIza",
        "-----BEGIN PRIVATE KEY-----",
    ]

    masked = text
    for r in replacements:
        masked = masked.replace(r, "[REDACTED]")

    return masked


def run_review(payload: dict, token: str):
    pr = payload["pull_request"]
    files_url = pr["url"] + "/files"

    files = github_get(files_url, token)

    diff_text = ""
    for f in files:
        if f.get("patch"):
            diff_text += f"\n--- {f['filename']} ---\n"
            diff_text += f["patch"]

    if not diff_text.strip():
        return None

    review_parts = []

    # 1️⃣ SECURITY SCAN (always)
    secret_findings = scan_for_secrets(diff_text)
    for finding in secret_findings:
        review_parts.append(f"[HIGH] {finding}")

    # 2️⃣ MASK SECRETS BEFORE LLM
    sanitized_diff = mask_secrets(diff_text)

    # 3️⃣ LLM REVIEW (always runs)
    llm_review = review_code(sanitized_diff)
    if llm_review:
        review_parts.append(llm_review)

    return "\n".join(review_parts)

def normalize_review(text: str) -> str:
    seen = set()
    lines = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line in seen:
            continue
        seen.add(line)
        lines.append(line)

    return "\n".join(lines)
