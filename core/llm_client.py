"""
Thin wrapper around the Groq API.

This module is responsible only for communicating with the LLM.
Business rules, retries, validation and report generation remain
outside this file.

The evaluator expects this function to return a JSON string that
matches the LLMEvaluationOutput schema.
"""

from __future__ import annotations

import logging

from groq import Groq

from config import Config

logger = logging.getLogger(__name__)

_client: Groq | None = None


class LLMClientError(Exception):
    """Base class for all LLM client failures."""


class LLMAuthenticationError(LLMClientError):
    """Raised when the API key is missing or invalid."""


class LLMTimeoutError(LLMClientError):
    """Raised when the API request times out."""


def _get_client() -> Groq:
    global _client

    if _client is not None:
        return _client

    if not Config.GROQ_API_KEY:
        raise LLMAuthenticationError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your API key."
        )

    _client = Groq(
        api_key=Config.GROQ_API_KEY
    )

    return _client


def call_llm(system_instructions: str, user_prompt: str) -> str:
    """
    Sends a prompt to Groq and returns the raw JSON string.
    """

    client = _get_client()

    logger.debug(
        "Calling Groq model=%s temperature=%s",
        Config.MODEL_NAME,
        Config.TEMPERATURE,
    )

    try:

        response = client.chat.completions.create(

            model=Config.MODEL_NAME,

            temperature=Config.TEMPERATURE,

            response_format={"type": "json_object"},

            messages=[
                {
                    "role": "system",
                    "content": system_instructions,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

    except Exception as exc:

        error_text = str(exc).lower()

        if "authentication" in error_text or "api key" in error_text:
            raise LLMAuthenticationError(
                f"Groq rejected the API key: {exc}"
            ) from exc

        if "timeout" in error_text:
            raise LLMTimeoutError(
                f"Groq request timed out: {exc}"
            ) from exc

        raise LLMClientError(
            f"Groq client error: {exc}"
        ) from exc

    text = response.choices[0].message.content

    if not text or not text.strip():
        raise LLMClientError(
            "Groq returned an empty response."
        )

    return text