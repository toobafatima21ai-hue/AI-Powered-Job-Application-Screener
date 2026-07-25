"""
Writes the final evaluation report.

Responsibilities:
- Create output directory
- Serialize candidate evaluation results
- Add hiring summary statistics
- Save clean JSON report

No business decisions are made here.
This module only formats and writes results.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from models.schemas import EvaluationResult


logger = logging.getLogger(__name__)


class ReportWriteError(Exception):
    """Raised when the report cannot be written to disk."""


def _generate_summary(
    results: List[EvaluationResult]
) -> Dict[str, Any]:
    """
    Generate high-level recruitment statistics.

    This helps recruiters quickly understand
    the screening outcome without reading
    every candidate entry.
    """

    total_candidates = len(results)

    shortlisted = sum(
        1
        for result in results
        if result.verdict == "Shortlist"
    )

    rejected = sum(
        1
        for result in results
        if result.verdict == "Reject"
    )

    maybe = sum(
        1
        for result in results
        if result.verdict == "Maybe"
    )


    manual_review = sum(
        1
        for result in results
        if result.manual_review_required
    )


    average_score = (
        round(
            sum(result.match_score for result in results)
            / total_candidates,
            2,
        )
        if total_candidates
        else 0
    )


    return {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "total_candidates": total_candidates,

        "shortlisted_candidates": shortlisted,

        "maybe_candidates": maybe,

        "rejected_candidates": rejected,

        "manual_review_required": manual_review,

        "average_match_score": average_score,
    }



def write_report(
    results: List[EvaluationResult],
    output_path: str
) -> None:
    """
    Write final recruitment evaluation report.

    Output structure:

    {
        "summary": {...},
        "candidates": [...]
    }


    Args:
        results:
            Final evaluated candidates.

        output_path:
            JSON destination path.

    Raises:
        ReportWriteError:
            If writing fails.
    """


    path = Path(output_path)

    # Create output directory if missing
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    payload = {

        "summary": _generate_summary(results),

        "candidates": [
            result.model_dump()
            for result in results
        ],
    }



    try:

        path.write_text(
            json.dumps(
                payload,
                indent=2
            ),
            encoding="utf-8",
        )


    except OSError as exc:

        raise ReportWriteError(
            f"Could not write report to {output_path}: {exc}"
        ) from exc



    logger.info(
        "Report written to %s (%d candidates)",
        output_path,
        len(results),
    )