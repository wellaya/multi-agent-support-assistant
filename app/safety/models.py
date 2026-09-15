from dataclasses import dataclass, field


@dataclass
class GuardrailResult:
    flagged: bool
    reasons: list[str] = field(default_factory=list)
