"""
Orchestrates the evaluation of a single candidate:

    build prompt -> call LLM -> parse JSON -> validate (Pydantic)
        -> [retry with error feedback if invalid] -> apply business rules
        -> [safe fallback if still failing after all retries]

This is the "agentic" core of the pipeline: the retry loop is not just
"call the API again and hope" — on each retry, the previous invalid
response and the specific validation error are appended to the prompt,
so the model gets targeted feedback instead of a blind second attempt.
"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from core.llm_client import (
    LLMClientError,
    LLMTimeoutError,
    LLMAuthenticationError,
    call_llm,
)

from core.prompt_builder import (
    build_evaluation_prompt,
    get_system_instructions,
)

from core.validators import (
    apply_business_rules,
    needs_manual_review,
)

from config import Config

from models.schemas import (
    CandidateProfile,
    EvaluationResult,
    LLMEvaluationOutput,
)

logger = logging.getLogger(__name__)


def _parse_and_validate(raw_text: str) -> LLMEvaluationOutput:
    """
    Parse raw LLM text as JSON and validate it against the schema.

    Raises:
        ValueError: if the response is not valid JSON.
        ValidationError: if JSON does not match schema.
    """

    try:
        data = json.loads(raw_text)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Response is not valid JSON: {exc}"
        ) from exc

    return LLMEvaluationOutput(**data)



def _build_retry_prompt(
    original_prompt: str,
    previous_response: str,
    error: str
) -> str:
    """
    Append previous invalid response and validation feedback
    so the LLM can correct itself.
    """

    return (
        f"{original_prompt}\n\n"
        "---\n"
        "Your previous response failed validation and could not be used.\n\n"
        f"Previous response:\n{previous_response}\n\n"
        f"Validation error:\n{error}\n\n"
        "Return a corrected JSON object that strictly follows "
        "the required schema.\n"
        "Output ONLY the JSON object, nothing else."
    )



def _fallback_result(
    candidate: CandidateProfile,
    reason: str
) -> EvaluationResult:
    """
    Safe fallback when LLM evaluation fails.

    We return Maybe because infrastructure failure should never
    automatically reject a candidate.
    """

    return EvaluationResult(
        candidate_id=candidate.candidate_id,
        name=candidate.name,
        verdict="Maybe",
        match_score=0,
        reason=(
            "Automated evaluation failed — flagged for manual review. "
            f"({reason})"
        ),
        reasoning="N/A — evaluation could not be completed.",
        rule_override_applied=False,
        manual_review_required=True,
    )



def evaluate_candidate(
    job_requirements_text: str,
    candidate: CandidateProfile
) -> EvaluationResult:
    """
    Evaluate a single candidate against job requirements.

    Never raises. Any unrecoverable failure returns a safe fallback
    result so one failed candidate does not stop batch processing.
    """

    prompt = build_evaluation_prompt(
        job_requirements_text,
        candidate
    )

    system_instructions = get_system_instructions()

    last_error = "unknown error"

    attempts = Config.MAX_RETRIES + 1


    for attempt in range(1, attempts + 1):

        logger.info(
            "Evaluating candidate %s (attempt %d/%d)",
            candidate.candidate_id,
            attempt,
            attempts,
        )


        try:

            raw_response = call_llm(
                system_instructions,
                prompt
            )


        except LLMAuthenticationError as exc:

            logger.error(
                "Authentication error evaluating %s: %s",
                candidate.candidate_id,
                exc,
            )

            return _fallback_result(
                candidate,
                f"authentication error: {exc}"
            )


        except LLMTimeoutError as exc:

            logger.warning(
                "Timeout evaluating %s on attempt %d: %s",
                candidate.candidate_id,
                attempt,
                exc,
            )

            last_error = str(exc)
            continue


        except LLMClientError as exc:

            logger.warning(
                "LLM error evaluating %s on attempt %d: %s",
                candidate.candidate_id,
                attempt,
                exc,
            )

            last_error = str(exc)
            continue



        try:

            llm_output = _parse_and_validate(
                raw_response
            )


        except (ValueError, ValidationError) as exc:

            logger.warning(
                "Validation failed for %s on attempt %d: %s",
                candidate.candidate_id,
                attempt,
                exc,
            )

            last_error = str(exc)

            prompt = _build_retry_prompt(
                prompt,
                raw_response,
                str(exc)
            )

            continue



        logger.info(
            "Candidate %s evaluated: verdict=%s score=%d",
            candidate.candidate_id,
            llm_output.verdict,
            llm_output.match_score,
        )


        # Apply deterministic business rules
        result = apply_business_rules(
            candidate,
            llm_output
        )


        # Mark candidates requiring human recruiter review
        result.manual_review_required = needs_manual_review(
            result
        )


        return result



    logger.error(
        "Candidate %s failed after %d attempts, "
        "returning fallback. Last error: %s",
        candidate.candidate_id,
        attempts,
        last_error,
    )


    return _fallback_result(
        candidate,
        last_error
    )