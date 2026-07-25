# AI-Powered Job Application Screener

An agentic Python pipeline that reads job requirements and candidate profiles, evaluates each
candidate against the role using an LLM (Google Gemini), and produces a structured JSON report
with a `Shortlist` / `Reject` / `Maybe` verdict, a 0–100 match score, and a human-readable reason
per candidate.

## Overview

Hiring teams need to triage large volumes of applications quickly and consistently. This project
builds a small but production-inspired agent that:

1. Reads job requirements from a plain-text (or JSON) file.
2. Reads candidate profiles from a CSV file.
3. Evaluates each candidate against the requirements using an LLM, forcing step-by-step reasoning
   before a verdict.
4. Applies a deterministic business-rule check for the two explicit disqualification rules stated
   in the job requirements (no Python experience at all / less than 1 year total experience) —
   regardless of what the LLM decided.
5. Writes a final JSON report to disk.

### Design philosophy: hybrid LLM + rules

The LLM is responsible for everything genuinely subjective: reasoning through each requirement,
scoring fit, deciding between `Shortlist` / `Reject` / `Maybe`, and writing the explanation. But
two disqualification rules are stated in the assignment as unambiguous, binary facts — "less than
1 year of total experience" and "no Python experience at all." Binary rules like these don't need
a language model's judgment; they need to be enforced the same way, every time. So they are
checked in plain Python (`core/validators.py`) *after* the LLM responds, and only override the
verdict when a rule is actually violated. A subjective `Maybe` from the LLM is never touched
unless a hard rule was broken — the validator does not second-guess reasoning, only enforces the
two explicit constraints.

## Architecture

\```
job_reader.py ─┐
               ├─→ prompt_builder.py → llm_client.py → evaluator.py (parse, validate, retry loop)
candidate_reader.py ─┘                                          │
                                                                  ▼
                                                          validators.py (hard rule check)
                                                                  │
                                                                  ▼
                                                          report_writer.py → report.json
\```

`agent.py` is the only file that ties these together — it's intentionally thin so the whole
pipeline can be understood by reading one file top to bottom.

## Project Structure

\```
job-screening-agent/
├── agent.py                  # CLI entrypoint — orchestrates the pipeline
├── config.py                 # Loads .env, holds all tunable constants
├── core/
│   ├── job_reader.py          # Reads requirements.txt/json → raw text
│   ├── candidate_reader.py    # Reads CSV → list[CandidateProfile], skips malformed rows
│   ├── prompt_builder.py      # Builds the structured evaluation prompt
│   ├── llm_client.py          # Thin wrapper around the Gemini API
│   ├── evaluator.py           # Orchestrates: prompt → LLM → validate → retry → business rules
│   ├── validators.py          # Deterministic disqualification rule enforcement
│   └── report_writer.py       # Writes the final JSON report
├── models/
│   └── schemas.py             # Pydantic models: CandidateProfile, LLMEvaluationOutput, EvaluationResult
├── data/
│   ├── job_requirements.txt   # Sample job requirements
│   └── candidates.csv         # Sample candidates (5 rows)
├── output/
│   └── report.json            # Sample output (committed for reviewers to inspect)
├── logs/                      # Runtime logs (created automatically, .log files gitignored)
├── tests/
│   └── test_validators.py     # Offline unit tests for the business-rule validator
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
\```

## Installation

\```bash
git clone <your-repo-url>
cd job-screening-agent
python -m venv venv
source venv/bin/activate    # on Windows: venv\Scripts\activate
pip install -r requirements.txt
\```

## Dependencies

- `google-genai` — official Google SDK for the Gemini API (current SDK; the older
  `google-generativeai` package is deprecated and was deliberately not used here).
- `pydantic` — schema definition and validation for both candidate input data and LLM output.
- `python-dotenv` — loads `GEMINI_API_KEY` and other settings from `.env`.

## API Key Setup

1. Get a free Gemini API key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
2. Copy the example env file:
   \```bash
   cp .env.example .env
   \```
3. Open `.env` and set:
   \```
   GEMINI_API_KEY=your_actual_key_here
   \```

The key is never hardcoded anywhere in the codebase, and `.env` is gitignored.

## Run Instructions

\```bash
python agent.py --job data/job_requirements.txt --candidates data/candidates.csv
\```

## CLI Examples

\```bash
# Basic run using the sample data
python agent.py --job data/job_requirements.txt --candidates data/candidates.csv

# Custom output path
python agent.py --job data/job_requirements.txt --candidates data/candidates.csv --output output/custom_report.json

# Verbose logging (useful for debugging retries)
python agent.py --job data/job_requirements.txt --candidates data/candidates.csv --log-level DEBUG

# JSON-format job requirements are also supported
python agent.py --job data/job_requirements.json --candidates data/candidates.csv
\```

Console output after a run:

\```
==================================================
SCREENING COMPLETE
==================================================
Total candidates evaluated : 5
  Shortlist  : 2
  Maybe      : 2
  Reject     : 1
Report written to          : output/report.json
==================================================
\```

## Example Output

See [`output/report.json`](output/report.json) for a full sample. Excerpt:

\```json
{
  "candidate_id": "C001",
  "name": "Sara Ahmed",
  "verdict": "Shortlist",
  "match_score": 95,
  "reason": "3 years Python, REST API confirmed, AI/ML project completed, and strong good-to-have coverage with FastAPI and AWS.",
  "reasoning": "Must Have check: python_years=3 satisfies the 2-year minimum. ...",
  "rule_override_applied": false
}
\```

`rule_override_applied` is `true` whenever the deterministic disqualification check overrode the
LLM's verdict — this makes every override auditable rather than silent.

## Screenshots

_Add a terminal screenshot of a run, and/or a screenshot of `output/report.json` opened in your
editor, here before submitting._

`[ Screenshot placeholder — terminal run output ]`

`[ Screenshot placeholder — sample report.json ]`

## Error Handling & Edge Cases

| Scenario | Behavior |
|---|---|
| Job requirements file missing/empty | Fails fast with a clear error before any LLM calls are made |
| Candidates CSV missing/unreadable | Fails fast with a clear error |
| A single CSV row is malformed (missing ID/name) | That row is skipped and logged; the rest of the batch proceeds |
| Numeric field is blank/non-numeric ("NaN", "n/a", text) | Coerced to `0.0` rather than crashing |
| LLM returns malformed JSON | Retried (up to `MAX_RETRIES`) with the validation error fed back into the prompt |
| LLM output fails Pydantic schema validation | Same retry loop as above |
| All retries exhausted | Candidate gets a safe fallback result: `verdict="Maybe"`, flagged for manual review — never a crash |
| Invalid/missing API key | Fails fast for that candidate (not retried, since retrying won't help) with a clear log message |
| API timeout | Retried, subject to the same retry budget |
| Candidate has 0 Python years or < 1 year total experience | Deterministically forced to `Reject`, regardless of the LLM's verdict |

## Configuration

All tunables live in `.env` / `config.py` — nothing is hardcoded in the pipeline:

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Your Gemini API key |
| `MODEL_NAME` | `gemini-2.0-flash` | Gemini model used for evaluation |
| `TEMPERATURE` | `0.1` | Lower = more deterministic, consistent verdicts |
| `LLM_TIMEOUT_SECONDS` | `30` | Per-call timeout |
| `MAX_RETRIES` | `2` | Retry attempts after an invalid/failed response |
| `MIN_TOTAL_EXPERIENCE_YEARS` | `1` | Disqualification threshold |
| `MIN_PYTHON_YEARS_FOR_DISQUALIFY` | `0` | Below/equal this = "no Python experience at all" |

## Running Tests

\```bash
python -m pytest tests/ -v
\```

The test suite covers the business-rule validator offline (no API calls needed) — including the
key "hybrid" behavior that a subjective `Maybe` verdict is never touched unless a hard rule is
violated.

## Future Improvements

- **Batch/async evaluation** — evaluate candidates concurrently with `asyncio` instead of
  sequentially, for larger candidate pools.
- **Fallback model chain** — if Gemini is unavailable, fall back to a secondary provider (mirrors
  a pattern I've used in a previous project) rather than failing the whole run.
- **Confidence-aware retries** — currently every invalid response gets the same retry treatment;
  a smarter version could distinguish "malformed JSON" (worth retrying) from "safety-filtered"
  (not worth retrying).
- **Structured requirements parsing as an optional mode** — for job postings with a very
  consistent format, an optional structured parser could reduce LLM calls, while still falling
  back to the current free-text approach for anything irregular.
- **Web UI** — a lightweight Streamlit front end for uploading a CSV and viewing verdicts, similar
  to my other portfolio projects.

## My Approach (for the submission email)

I designed this as a hybrid LLM + deterministic-rules pipeline: the LLM performs all subjective
reasoning, scoring, and the Shortlist/Reject/Maybe judgment call with an explicit chain-of-thought
requirement, while the two explicit disqualification rules from the job requirements are enforced
in code after the LLM responds — auditable via a `rule_override_applied` flag — so a binary
business rule is never left to probabilistic judgment. Every input boundary (CSV parsing, LLM
JSON output) is validated with Pydantic, with a retry loop that feeds validation errors back to
the model, and a safe non-crashing fallback if retries are exhausted. With more time, I'd add
concurrent evaluation and a fallback model chain for provider resilience.
