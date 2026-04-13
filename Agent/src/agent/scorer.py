"""Resume scoring logic using Gemini 2.5 Flash (its free) .

This module exposes a single public function, `score_resume`, which:
  1. Formats the resume and job description into the scorer prompt.
  2. Calls Gemini 2.5 Flash via LangChain (automatically traced by LangSmith).
  3. Parses and returns the structured JSON assessment.
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.prompts import RESUME_SCORER_SYSTEM, RESUME_SCORER_USER_TEMPLATE

_GEMINI_MODEL = "gemini-2.5-flash"

# Lazily initialised — created on first call so that importing this module does
# not require GOOGLE_API_KEY to be set (unit tests never call score_resume).
_llm: ChatGoogleGenerativeAI | None = None


def _get_llm() -> ChatGoogleGenerativeAI:
    """Return the shared LLM client, creating it on the first call.

    Deferred instantiation means the API key is only validated when
    ``score_resume`` is actually invoked, not at import time.
    """
    global _llm
    if _llm is None:
        # Single shared instance — avoids re-reading credentials and
        # re-initialising the transport on every call. 60 s timeout prevents a
        # hung API call from stalling the pipeline indefinitely.
        _llm = ChatGoogleGenerativeAI(model=_GEMINI_MODEL, request_timeout=60)
    return _llm


async def score_resume(jd_text: str, resume_text: str) -> dict:
    """Score a resume against a job description using Gemini 2.5 Flash.

    Args:
        jd_text: Clean job description text (output of ``scrape_job_description``).
        resume_text: The candidate's resume as plain text.

    Returns:
        Parsed assessment dict matching the resume scorer output schema:
            {
                "match_score":      int,          # 0–100
                "matched_skills":   list[str],
                "missing_skills":   list[str],
                "experience_gap":   str,
                "top_improvements": list[dict],   # action / reason / priority
                "summary":          str,
            }

    Raises:
        ValueError: If the LLM response cannot be parsed as valid JSON dict.
    """
    messages = [
        SystemMessage(content=RESUME_SCORER_SYSTEM),
        HumanMessage(
            content=RESUME_SCORER_USER_TEMPLATE.format(
                resume_text=resume_text,
                jd_text=jd_text,
            )
        ),
    ]

    response = await _get_llm().ainvoke(messages)
    return _parse_json(response.content)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_json(raw: str) -> dict:
    """Strip optional markdown fences and parse JSON from an LLM response.

    Some models wrap their output in ```json ... ``` blocks despite being
    instructed not to. This function handles both the clean and wrapped cases.

    Args:
        raw: Raw string content from the LLM response.

    Returns:
        Parsed JSON as a dict.

    Raises:
        ValueError: If the cleaned string is not valid JSON.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned non-JSON output. First 200 chars: {raw[:200]!r}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError(
            f"LLM returned valid JSON but not an object (got {type(parsed).__name__}). "
            f"First 200 chars: {raw[:200]!r}"
        )

    return parsed
