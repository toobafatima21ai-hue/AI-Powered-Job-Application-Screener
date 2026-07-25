#!/usr/bin/env python3
"""
CLI entrypoint for the AI-Powered Job Application Screener.

Usage:
    python agent.py --job data/job_requirements.txt --candidates data/candidates.csv
    python agent.py --job data/job_requirements.txt --candidates data/candidates.csv --output output/report.json

This file is intentionally thin. It should read like pseudocode:
parse args -> configure logging -> read job -> read candidates ->
evaluate each -> write report -> print summary. All actual logic lives
in core/ — if you can't follow the whole pipeline by reading this file
top to bottom, the architecture has failed at its job.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from config import Config
from core.candidate_reader import CandidateFileError, read_candidates
from core.evaluator import evaluate_candidate
from core.job_reader import JobRequirementsError, read_job_requirements
from core.report_writer import ReportWriteError, write_report


def _setup_logging(log_level: str) -> None:
    """Configure logging to both console and a rotating-by-run log file."""
    log_dir = Path(Config.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "agent.log", encoding="utf-8"),
        ],
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent.py",
        description="AI-powered job application screening agent.",
    )
    parser.add_argument(
        "--job",
        required=True,
        help="Path to the job requirements file (.txt or .json).",
    )
    parser.add_argument(
        "--candidates",
        required=True,
        help="Path to the candidates CSV file.",
    )
    parser.add_argument(
        "--output",
        default=Config.DEFAULT_OUTPUT_PATH,
        help=f"Path to write the JSON report to (default: {Config.DEFAULT_OUTPUT_PATH}).",
    )
    parser.add_argument(
        "--log-level",
        default=Config.LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: %(default)s).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    _setup_logging(args.log_level)
    logger = logging.getLogger("agent")

    try:
        Config.validate()
    except EnvironmentError as exc:
        logger.error(str(exc))
        return 1

    try:
        job_requirements_text = read_job_requirements(args.job)
    except JobRequirementsError as exc:
        logger.error("Failed to read job requirements: %s", exc)
        return 1

    try:
        candidates = read_candidates(args.candidates)
    except CandidateFileError as exc:
        logger.error("Failed to read candidates: %s", exc)
        return 1

    logger.info("Starting evaluation of %d candidate(s)...", len(candidates))
    results = [evaluate_candidate(job_requirements_text, candidate) for candidate in candidates]

    try:
        write_report(results, args.output)
    except ReportWriteError as exc:
        logger.error("Failed to write report: %s", exc)
        return 1

    _print_summary(results, args.output)
    return 0


def _print_summary(results, output_path: str) -> None:
    counts = {"Shortlist": 0, "Reject": 0, "Maybe": 0}
    for result in results:
        counts[result.verdict] += 1

    print("\n" + "=" * 50)
    print("SCREENING COMPLETE")
    print("=" * 50)
    print(f"Total candidates evaluated : {len(results)}")
    print(f"  Shortlist  : {counts['Shortlist']}")
    print(f"  Maybe      : {counts['Maybe']}")
    print(f"  Reject     : {counts['Reject']}")
    print(f"Report written to          : {output_path}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    sys.exit(main())