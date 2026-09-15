import re

from app.safety.models import GuardrailResult

PII_PATTERNS = {
    "email": r"\b[\w.-]+@[\w.-]+\.\w+\b",
    "phone": r"\b(\+?\d{1,2}[ -]?)?\(?\d{3}\)?[ -]\d{3}[ -]\d{4}\b",
    "credit_card": r"\b\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{4}\b|\b\d{13,16}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
}

POLICY_PHRASES = [
    "100% guaranteed",
    "we promise",
    "no matter what",
    "unlimited refund",
]

_COMPILED_PII_PATTERNS = {name: re.compile(pattern) for name, pattern in PII_PATTERNS.items()}


def check_output(text: str) -> GuardrailResult:
    reasons = []

    for name, pattern in _COMPILED_PII_PATTERNS.items():
        if pattern.search(text):
            reasons.append(f"possible_pii:{name}")

    lowered = text.lower()
    for phrase in POLICY_PHRASES:
        if phrase in lowered:
            reasons.append(f"policy_phrase:{phrase}")

    return GuardrailResult(flagged=bool(reasons), reasons=reasons)
