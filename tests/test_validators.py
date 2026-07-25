"""
Unit tests for core/validators.py.

These deliberately avoid any network/LLM calls — validators.py is pure
business logic operating on already-validated Pydantic models, so it
can (and should) be fully tested offline. This is also the single
highest-value place to have tests in this project: it's where a bug
would silently let a disqualified candidate through, or wrongly reject
a qualified one.

Run with: python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.validators import apply_business_rules
from models.schemas import CandidateProfile, LLMEvaluationOutput


def _make_candidate(**overrides) -> CandidateProfile:
    defaults = dict(
        candidate_id="C999",
        name="Test Candidate",
        python_years=3,
        total_exp=4,
        rest_api=True,
        ai_ml_project=True,
        framework="FastAPI",
        cloud="AWS",
    )
    defaults.update(overrides)
    return CandidateProfile(**defaults)


def _make_llm_output(**overrides) -> LLMEvaluationOutput:
    defaults = dict(
        reasoning="Meets all requirements.",
        verdict="Shortlist",
        match_score=90,
        reason="Strong match.",
    )
    defaults.update(overrides)
    return LLMEvaluationOutput(**defaults)


def test_qualified_candidate_is_not_overridden():
    candidate = _make_candidate()
    llm_output = _make_llm_output(verdict="Shortlist")

    result = apply_business_rules(candidate, llm_output)

    assert result.verdict == "Shortlist"
    assert result.rule_override_applied is False


def test_zero_python_years_forces_reject():
    candidate = _make_candidate(python_years=0)
    llm_output = _make_llm_output(verdict="Shortlist")  # LLM incorrectly says Shortlist

    result = apply_business_rules(candidate, llm_output)

    assert result.verdict == "Reject"
    assert result.rule_override_applied is True


def test_under_one_year_total_experience_forces_reject():
    candidate = _make_candidate(total_exp=0.5)
    llm_output = _make_llm_output(verdict="Maybe")

    result = apply_business_rules(candidate, llm_output)

    assert result.verdict == "Reject"
    assert result.rule_override_applied is True


def test_llm_reject_is_not_double_flagged_as_override():
    # If the LLM already said Reject and a hard rule is also violated,
    # rule_override_applied should be False since no verdict change occurred.
    candidate = _make_candidate(python_years=0)
    llm_output = _make_llm_output(verdict="Reject")

    result = apply_business_rules(candidate, llm_output)

    assert result.verdict == "Reject"
    assert result.rule_override_applied is False


def test_maybe_verdict_is_preserved_when_no_hard_rule_violated():
    # This is the key "hybrid" behavior: a subjective Maybe from the LLM
    # must NOT be touched by the validator when no hard rule is broken.
    candidate = _make_candidate(python_years=1, ai_ml_project=False)
    llm_output = _make_llm_output(verdict="Maybe", match_score=55)

    result = apply_business_rules(candidate, llm_output)

    assert result.verdict == "Maybe"
    assert result.rule_override_applied is False


def test_borderline_total_exp_exactly_at_threshold_is_not_disqualified():
    candidate = _make_candidate(total_exp=1.0)
    llm_output = _make_llm_output(verdict="Maybe")

    result = apply_business_rules(candidate, llm_output)

    assert result.verdict == "Maybe"
    assert result.rule_override_applied is False