from typing import Literal

from pydantic import BaseModel, Field


class TriageResult(BaseModel):
    category: Literal[
        "password_reset",
        "billing",
        "refund",
        "shipping",
        "account_deletion",
        "other",
    ] = Field(description="The support topic that best matches the customer's message.")
    sentiment: Literal["neutral", "frustrated", "angry"] = Field(
        description="The customer's emotional tone."
    )
    needs_escalation: bool = Field(
        description=(
            "True if the customer is angry, threatens a chargeback/legal action, "
            "or the request clearly requires a human (e.g. suspected fraud, "
            "account compromise)."
        )
    )
    reasoning: str = Field(description="One sentence explaining the classification.")
