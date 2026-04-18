from __future__ import annotations

from enum import Enum
from typing import TypedDict
from typing_extensions import NotRequired


class RequestType(Enum):
    score = 0
    question = 1


class State(TypedDict):
    # ── inputs (required at invoke time) ──────────────────────────────────────
    user_id: str
    request_type: RequestType
    job_url: str

    # ── populated during execution ────────────────────────────────────────────
    resume_text: NotRequired[str]
    job_description: NotRequired[str]
    score_result: NotRequired[dict]
    user_question: NotRequired[str]
    ai_answer: NotRequired[str]


