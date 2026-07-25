"""
Reads the job requirements file.

Deliberately "dumb": it reads the file as raw text and hands that
straight to the prompt builder. We do NOT regex-parse "Must Have /
Good to Have / Disqualify If" into structured Python objects — the LLM
is far better at that kind of flexible NLU than a hand-rolled parser
would be, and a parser would be brittle against wording changes. The
only structured parsing we do ourselves is for the small set of hard
disqualification thresholds, and those live in config.py / validators.py
as explicit numeric rules, not as text extracted from this file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class JobRequirementsError(Exception):
    """Raised when the job requirements file cannot be read or is empty."""


def read_job_requirements(path: str) -> str:
    """Read job requirements from a .txt or .json file and return raw text.

    Args:
        path: Path to a plain-text or JSON job requirements file.

    Returns:
        The requirements as a single string, suitable for embedding
        directly into the LLM prompt.

    Raises:
        JobRequirementsError: if the file is missing, unreadable, or empty.
    """
    file_path = Path(path)
    logger.info("Reading job requirements from %s", file_path)

    if not file_path.exists():
        raise JobRequirementsError(f"Job requirements file not found: {path}")

    try:
        raw_text = file_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise JobRequirementsError(f"Could not read job requirements file: {exc}") from exc

    if not raw_text:
        raise JobRequirementsError(f"Job requirements file is empty: {path}")

    if file_path.suffix.lower() == ".json":
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise JobRequirementsError(f"Job requirements file is not valid JSON: {exc}") from exc
        # Re-serialize with indentation for a clean, readable prompt block,
        # regardless of how the source JSON was formatted.
        raw_text = json.dumps(parsed, indent=2)

    logger.debug("Job requirements loaded (%d characters)", len(raw_text))
    return raw_text