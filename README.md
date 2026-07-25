# AI-Powered Job Application Screener

An agentic Python-based recruitment screening pipeline that evaluates candidates against job requirements using an LLM-powered reasoning system combined with deterministic business rules.

The system reads job requirements and candidate profiles, evaluates candidate-job fit using Groq LLM models, applies rule-based validation, identifies candidates requiring human review, and generates a structured JSON hiring report.

---

# Overview

Hiring teams often receive many applications and need a consistent way to identify strong candidates.

This project builds a production-inspired AI screening agent that:

1. Reads job requirements from a text file.
2. Reads candidate profiles from CSV files.
3. Uses an LLM to analyze candidate suitability.
4. Evaluates every requirement individually.
5. Generates:
   - Shortlist
   - Reject
   - Maybe

   decisions with explanations.
6. Applies deterministic business rules for critical disqualification conditions.
7. Flags uncertain candidates for manual review.
8. Produces a structured JSON report containing evaluation results and summary statistics.

---

# Key Features

## Hybrid AI + Rule-Based Architecture

The system combines:

### LLM Responsibilities

The LLM handles subjective tasks:

- Requirement comparison
- Candidate reasoning
- Match scoring
- Shortlist / Reject / Maybe decision
- Human-readable explanation


### Deterministic Validator Responsibilities

Python rules handle objective decisions:

- Less than 1 year total experience
- No Python experience
- Manual review detection

This prevents important business rules from depending only on probabilistic LLM output.

---

# Architecture

```
                    Job Requirements
                           |
                           |
                    Candidate Profiles
                           |
                           v

                 prompt_builder.py
                 (Structured Prompt)

                           |
                           v

                  llm_client.py
                  (Groq API)

                           |
                           v

                  evaluator.py
       (Parse → Validate → Retry → Process)

                           |
                           v

                 validators.py
        (Hard Rules + Manual Review)

                           |
                           v

              report_writer.py

                           |
                           v

                 report.json
```

`agent.py` acts as the main pipeline controller connecting all components.

---

# Project Structure

```
job-screening-agent/

├── agent.py
├── config.py

├── core/
│   ├── job_reader.py
│   ├── candidate_reader.py
│   ├── prompt_builder.py
│   ├── llm_client.py
│   ├── evaluator.py
│   ├── validators.py
│   └── report_writer.py

├── models/
│   └── schemas.py

├── data/
│   ├── job_requirements.txt
│   ├── candidates.csv
│   └── test_edge_candidates.csv

├── output/
│   └── report.json

├── logs/

├── tests/

├── .env.example
├── requirements.txt
└── README.md
```

---

# Installation

Clone the repository:

```bash
git clone <your-repo-url>

cd job-screening-agent
```

Create virtual environment:

```bash
python -m venv venv
```

Activate environment:

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# API Key Setup

This project uses Groq API for LLM inference.

Create a free Groq API key from:

```
https://console.groq.com/
```

Create environment file:

```bash
copy .env.example .env
```

or manually create:

```
.env
```

Add:

```env
GROQ_API_KEY=your_api_key_here
```

The API key is never hardcoded inside the project.

---

# Configuration

All configurable values are stored inside:

```
config.py
```

and loaded from `.env`.

Example:

| Variable | Purpose |
|---|---|
| GROQ_API_KEY | Groq authentication key |
| MODEL_NAME | LLM model name |
| TEMPERATURE | Controls randomness |
| LLM_TIMEOUT_SECONDS | API timeout |
| MAX_RETRIES | Invalid response retry count |
| MIN_TOTAL_EXPERIENCE_YEARS | Hard rejection threshold |
| MIN_PYTHON_YEARS_FOR_DISQUALIFY | Python experience rule |

Example:

```env
MODEL_NAME=llama-3.3-70b-versatile
TEMPERATURE=0
MAX_RETRIES=2
```

---

# Running the Application

## Normal Candidate Evaluation

Run:

```bash
python agent.py \
--job data/job_requirements.txt \
--candidates data/candidates.csv
```

The generated report will be saved:

```
output/report.json
```

---

# Edge Case Testing

The project includes:

```
data/test_edge_candidates.csv
```

This dataset tests:

- Missing information
- Borderline experience
- Weak candidates
- Ambiguous skills
- Human review scenarios


Run:

```bash
python agent.py \
--job data/job_requirements.txt \
--candidates data/test_edge_candidates.csv
```

---

# Output Report

The generated JSON report contains:

## Summary

Example:

```json
{
 "total_candidates":5,
 "shortlisted_candidates":2,
 "maybe_candidates":1,
 "rejected_candidates":2,
 "manual_review_required":2,
 "average_match_score":65
}
```

## Candidate Evaluation

Example:

```json
{
 "candidate_id":"C001",
 "name":"Sara Ahmed",
 "verdict":"Shortlist",
 "match_score":95,
 "reason":"Strong Python backend developer with AI/ML experience.",
 "reasoning":"Candidate satisfies all Must Have requirements.",
 "manual_review_required":false
}
```

---

# LLM Evaluation Strategy

The prompt forces the model to:

1. Analyze every Must Have requirement.
2. Analyze Good To Have skills.
3. Identify missing information.
4. Explain strengths and weaknesses.
5. Select an appropriate verdict.

The model is instructed:

- Never invent experience.
- Never assume missing skills.
- Prefer Maybe when uncertainty exists.

---

# Verdict Logic

## Shortlist

Used when:

- All Must Have requirements are satisfied.
- Candidate has relevant additional skills.
- No critical ambiguity exists.


## Reject

Used when:

- Candidate fails important requirements.
- Candidate violates hard disqualification rules.


## Maybe

Used when:

- Candidate is borderline.
- Important information is missing.
- Human review is recommended.

---

# Edge Case Handling

| Scenario | System Behavior |
|---|---|
| Missing candidate fields | Marked as unclear/not provided |
| Weak candidate profile | Evaluated normally and rejected if unsuitable |
| Borderline experience | May trigger Maybe/manual review |
| Invalid LLM JSON | Automatic retry with validation feedback |
| API failure | Safe fallback response |
| Hard rule violation | Deterministic Reject override |
| Ambiguous candidate | manual_review_required=true |

---

# Code Quality Principles

The project follows:

- Modular architecture
- Separation of responsibilities
- Pydantic schema validation
- Error handling
- Logging
- Deterministic rule enforcement
- Retry-based LLM reliability

Each component has a single responsibility:

| File | Responsibility |
|-|-|
| llm_client.py | Communicates with Groq |
| prompt_builder.py | Creates evaluation prompts |
| evaluator.py | Controls evaluation workflow |
| validators.py | Applies business rules |
| report_writer.py | Generates final report |

---

# Testing

Run:

```bash
pytest tests/ -v
```

The tests validate deterministic business rules without requiring API calls.

---

# Future Improvements

Possible extensions:

- Streamlit recruiter dashboard
- Batch candidate processing
- Async LLM evaluation
- Multiple LLM provider fallback
- Resume PDF parsing
- Vector database based candidate search
- Interview question generation

---

# My Approach

I designed this system as a hybrid AI recruitment agent.

The LLM performs complex reasoning tasks such as requirement matching, scoring, and generating explanations.

However, critical hiring rules are enforced through deterministic Python validation to ensure reliability and consistency.

The system also handles uncertainty using a manual review mechanism instead of forcing every candidate into only accept or reject categories.

This architecture creates a safer and more realistic AI-assisted recruitment workflow.
