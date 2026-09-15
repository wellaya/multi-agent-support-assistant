import re

from app.safety.models import GuardrailResult

INJECTION_PATTERNS = [
    r"ignore (all|any|the)? ?(previous|prior|above) instructions",
    r"disregard (all|any|the)? ?(previous|prior|above)",
    r"you are now (in )?(dan|jailbreak|developer) mode",
    r"reveal (your|the) (system prompt|instructions)",
    r"act as (if you were|an unrestricted)",
    r"pretend (you have no|there are no) (restrictions|rules|guidelines)",
    r"forget (everything|all) (you (were|are) told|previous instructions)",
    r"\bsystem prompt\b",
    r"new instructions:",
]

_COMPILED_PATTERNS = [re.compile(pattern) for pattern in INJECTION_PATTERNS]


def check_input(message: str) -> GuardrailResult:
    lowered = message.lower()
    reasons = [
        pattern.pattern for pattern in _COMPILED_PATTERNS if pattern.search(lowered)
    ]
    return GuardrailResult(flagged=bool(reasons), reasons=reasons)
