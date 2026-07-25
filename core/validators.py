"""
Deterministic business-rule enforcement.

Hybrid architecture:

LLM Responsibilities:
- Candidate reasoning
- Requirement comparison
- Match scoring
- Shortlist / Reject / Maybe decision

Validator Responsibilities:
- Hard disqualification rules
- Manual review identification
- Final deterministic safety checks

Hard disqualification rules:

    Disqualify If:
    - Less than 1 year total experience
    - No Python experience

Manual review rules:

    Require Human Review If:
    - Candidate verdict is Maybe
    - Candidate score is borderline
    - Candidate evidence is unclear

The purpose of this layer is to keep final decisions
safe and deterministic.
"""

from __future__ import annotations

import logging
from typing import Tuple

from config import Config
from models.schemas import (
    CandidateProfile,
    EvaluationResult,
    LLMEvaluationOutput,
)


logger = logging.getLogger(__name__)


_DISQUALIFICATION_REASON_TEMPLATE = (
    "Overridden to Reject by deterministic business rule: {rule}. "
    "(LLM original assessment: {original_reason})"
)


def _violates_hard_rules(
    candidate: CandidateProfile
) -> Tuple[bool, str]:
    """
    Check mandatory disqualification rules.

    Returns:
        Tuple:
        (
            True/False,
            explanation
        )
    """

    # Rule 1:
    # Candidate must have minimum total experience
    if candidate.total_exp < Config.MIN_TOTAL_EXPERIENCE_YEARS:
        return (
            True,
            (
                f"total experience ({candidate.total_exp} yrs) "
                f"is below required minimum of "
                f"{Config.MIN_TOTAL_EXPERIENCE_YEARS} years"
            ),
        )


    # Rule 2:
    # Candidate must have Python experience
    if candidate.python_years <= Config.MIN_PYTHON_YEARS_FOR_DISQUALIFY:
        return (
            True,
            "candidate has no Python experience",
        )


    return False, ""



def needs_manual_review(
    llm_output: LLMEvaluationOutput
) -> bool:
    """
    Determine whether human review is required.

    Manual review should happen when:

    1. LLM verdict is Maybe
    2. Candidate score is borderline
    3. Candidate is neither a clear hire nor reject

    This prevents uncertain candidates from being
    automatically accepted or rejected.
    """

    # LLM itself requested human judgement
    if llm_output.verdict == "Maybe":
        return True


    # Borderline score range
    # 40-75 means candidate has some strengths
    # but also meaningful gaps
    if 40 <= llm_output.match_score <= 75:
        return True


    return False



def apply_business_rules(
    candidate: CandidateProfile,
    llm_output: LLMEvaluationOutput,
) -> EvaluationResult:
    """
    Combine LLM recommendation with deterministic rules.

    Pipeline:

    1. Check hard disqualification rules.
    2. Override unsafe LLM decisions.
    3. Determine manual review requirement.
    4. Return final evaluation.
    """


    violated, rule_description = _violates_hard_rules(candidate)



    # ==================================================
    # HARD RULE OVERRIDE
    # ==================================================

    if violated and llm_output.verdict != "Reject":

        logger.warning(
            "Overriding candidate %s decision: %s -> Reject (%s)",
            candidate.candidate_id,
            llm_output.verdict,
            rule_description,
        )


        return EvaluationResult(
            candidate_id=candidate.candidate_id,
            name=candidate.name,
            verdict="Reject",

            # Reduce score because hard rule failed
            match_score=min(
                llm_output.match_score,
                20
            ),

            reason=_DISQUALIFICATION_REASON_TEMPLATE.format(
                rule=rule_description,
                original_reason=llm_output.reason,
            ),

            reasoning=llm_output.reasoning,

            rule_override_applied=True,

            manual_review_required=False,
        )



    # ==================================================
    # NORMAL EVALUATION
    # ==================================================

    manual_review = needs_manual_review(
        llm_output
    )


    if manual_review:
        logger.info(
            "Candidate %s flagged for manual review",
            candidate.candidate_id,
        )


    return EvaluationResult(
        candidate_id=candidate.candidate_id,
        name=candidate.name,

        verdict=llm_output.verdict,

        match_score=llm_output.match_score,

        reason=llm_output.reason,

        reasoning=llm_output.reasoning,

        rule_override_applied=False,

        manual_review_required=manual_review,
    )