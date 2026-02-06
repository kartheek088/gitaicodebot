from groq import Groq
from .config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


def review_code(diff: str) -> str:
    prompt = f"""
You are a senior software engineer reviewing a GitHub pull request.

ONLY comment on code present in the diff.

Classify findings as:
[HIGH] Security, auth, secrets, data loss
[MEDIUM] Bugs, missing error handling
[LOW] Maintainability, clarity

For [HIGH] findings, include filename if possible.
Example:
[HIGH] auth.py Possible hardcoded secret

Avoid duplicates.
If unsure, say: "Needs clarification".

Diff:
{diff}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content
