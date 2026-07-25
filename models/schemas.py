"""
Pydantic data models used across the pipeline.

Two categories of models live here:

1. Input models (`CandidateProfile`) — represent a row from candidates.csv
   after cleaning/coercion.

2. Output models:
   - LLMEvaluationOutput:
        Raw validated response returned by the LLM.

   - EvaluationResult:
        Final report object after deterministic validation,
        rule enforcement, and manual review tagging.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator



class CandidateProfile(BaseModel):
    """
    A cleaned candidate profile from candidates.csv.
    """

    candidate_id: str
    name: str

    python_years: float = 0.0
    total_exp: float = 0.0

    rest_api: bool = False
    ai_ml_project: bool = False

    framework: Optional[str] = None
    cloud: Optional[str] = None


    @field_validator("candidate_id", "name", mode="before")
    @classmethod
    def _strip_required_strings(
        cls,
        value: object
    ) -> str:

        if value is None:
            raise ValueError(
                "required field is missing"
            )

        text = str(value).strip()

        if not text:
            raise ValueError(
                "required field is blank"
            )

        return text



    @field_validator(
        "python_years",
        "total_exp",
        mode="before"
    )
    @classmethod
    def _coerce_numeric(
        cls,
        value: object
    ) -> float:

        if value is None:
            return 0.0


        text = str(value).strip().lower()


        if text in (
            "",
            "nan",
            "none",
            "n/a",
            "na"
        ):
            return 0.0


        try:
            return float(text)

        except ValueError:
            return 0.0



    @field_validator(
        "rest_api",
        "ai_ml_project",
        mode="before"
    )
    @classmethod
    def _coerce_yes_no(
        cls,
        value: object
    ) -> bool:

        if value is None:
            return False


        text = str(value).strip().lower()

        return text in (
            "yes",
            "y",
            "true",
            "1"
        )



    @field_validator(
        "framework",
        "cloud",
        mode="before"
    )
    @classmethod
    def _coerce_optional_string(
        cls,
        value: object
    ) -> Optional[str]:

        if value is None:
            return None


        text = str(value).strip()


        if not text or text.lower() in (
            "none",
            "no",
            "n/a",
            "na",
            "nan"
        ):
            return None


        return text





class LLMEvaluationOutput(BaseModel):
    """
    Schema for raw LLM JSON response.

    The LLM does NOT decide manual review.
    That decision belongs to validators.py.
    """


    reasoning: str = Field(
        ...,
        min_length=1,
        description=(
            "Step-by-step evaluation of the candidate "
            "against every requirement."
        )
    )


    verdict: Literal[
        "Shortlist",
        "Reject",
        "Maybe"
    ]


    match_score: int = Field(
        ...,
        ge=0,
        le=100
    )


    reason: str = Field(
        ...,
        min_length=1,
        description=(
            "Human-readable summary "
            "of the decision."
        )
    )



    @field_validator(
        "match_score",
        mode="before"
    )
    @classmethod
    def _clamp_score(
        cls,
        value: object
    ) -> int:

        try:
            score = int(
                round(
                    float(value)
                )
            )

        except (
            TypeError,
            ValueError
        ):
            raise ValueError(
                f"match_score is not valid: {value!r}"
            )


        return max(
            0,
            min(
                100,
                score
            )
        )





class EvaluationResult(BaseModel):
    """
    Final candidate evaluation written to report.json.

    Includes:
    - LLM decision
    - deterministic rule override status
    - manual recruiter review flag
    """


    candidate_id: str

    name: str


    verdict: Literal[
        "Shortlist",
        "Reject",
        "Maybe"
    ]


    match_score: int


    reason: str


    reasoning: str


    # True when validators.py changed the LLM decision
    rule_override_applied: bool = False


    # True when human recruiter review is recommended
    # because the case is uncertain or borderline
    manual_review_required: bool = False