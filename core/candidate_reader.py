"""
Reads candidates.csv and produces a clean list of CandidateProfile objects.

Uses the stdlib `csv` module rather than pandas: for a file with a
handful of rows, pandas is an unjustified dependency. All coercion of
messy values (Yes/No, blanks, stray whitespace) is delegated to the
Pydantic validators on CandidateProfile — this module's only job is to
get raw rows out of the file and into that model, and to make sure one
malformed row can't take down the entire batch.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List

from pydantic import ValidationError

from models.schemas import CandidateProfile

logger = logging.getLogger(__name__)


class CandidateFileError(Exception):
    """Raised when the candidates file cannot be read or contains no usable rows."""


def _normalize_headers(fieldnames: List[str]) -> List[str]:
    """Strip whitespace from CSV headers.

    The sample candidates.csv in the assignment has headers like
    "candidate_id, name, python_years" — note the space after each
    comma, which csv.DictReader would otherwise bake into the key
    names (" name" instead of "name").
    """
    return [name.strip() for name in fieldnames]


def read_candidates(path: str) -> List[CandidateProfile]:
    """Read and validate candidate rows from a CSV file.

    Rows that are individually malformed (e.g. missing a required
    identifier) are logged and skipped rather than crashing the whole
    read — one bad row should not block screening the other candidates.
    If ALL rows fail, that's treated as a fatal error since it almost
    certainly means the file format itself is wrong.

    Args:
        path: Path to candidates.csv.

    Returns:
        A list of validated CandidateProfile objects.

    Raises:
        CandidateFileError: if the file is missing, unreadable, or has
            no usable rows.
    """
    file_path = Path(path)
    logger.info("Reading candidates from %s", file_path)

    if not file_path.exists():
        raise CandidateFileError(f"Candidates file not found: {path}")

    try:
        with file_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise CandidateFileError(f"Candidates file has no header row: {path}")
            reader.fieldnames = _normalize_headers(reader.fieldnames)

            candidates: List[CandidateProfile] = []
            for row_number, row in enumerate(reader, start=2):  # header is row 1
                cleaned_row = {
                    (key.strip() if key else key): (value.strip() if isinstance(value, str) else value)
                    for key, value in row.items()
                    if key is not None
                }
                try:
                    candidate = CandidateProfile(**cleaned_row)
                    candidates.append(candidate)
                except ValidationError as exc:
                    logger.warning("Skipping malformed candidate row %d: %s", row_number, exc)
    except csv.Error as exc:
        raise CandidateFileError(f"Invalid CSV format in {path}: {exc}") from exc
    except OSError as exc:
        raise CandidateFileError(f"Could not read candidates file: {exc}") from exc

    if not candidates:
        raise CandidateFileError(f"No valid candidate rows found in {path}")

    logger.info("Loaded %d valid candidate(s)", len(candidates))
    return candidates