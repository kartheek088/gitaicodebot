import re
import math

SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",              # AWS
    r"AIza[0-9A-Za-z_-]{35}",         # Google API
    r"sk-[0-9a-zA-Z]{48}",             # OpenAI-like
    r"-----BEGIN PRIVATE KEY-----",   # Private keys
]


def _entropy(s: str) -> float:
    prob = [float(s.count(c)) / len(s) for c in set(s)]
    return -sum(p * math.log2(p) for p in prob)


def scan_for_secrets(text: str):
    findings = set()

    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text):
            findings.add("Hardcoded secret detected (pattern match)")

    for line in text.splitlines():
        if len(line) >= 20 and _entropy(line) > 4.5:
            findings.add("High-entropy string detected (possible secret)")

    return list(findings)
