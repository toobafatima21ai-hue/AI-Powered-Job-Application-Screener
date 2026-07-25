from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Holds all environment-derived and tunable settings."""

    # -------- LLM Provider --------
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    # -------- Retry --------
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))

    # -------- Business Rules --------
    MIN_TOTAL_EXPERIENCE_YEARS: float = float(
        os.getenv("MIN_TOTAL_EXPERIENCE_YEARS", "1")
    )
    MIN_PYTHON_YEARS_FOR_DISQUALIFY: float = float(
        os.getenv("MIN_PYTHON_YEARS_FOR_DISQUALIFY", "0")
    )

    # -------- Paths --------
    DEFAULT_OUTPUT_PATH: str = os.getenv(
        "DEFAULT_OUTPUT_PATH", "output/report.json"
    )
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")

    # -------- Logging --------
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> None:
        if not cls.GROQ_API_KEY:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
            )