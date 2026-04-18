"""Resume Scorer Agent — LangGraph pipeline.

Three-node workflow:
    fetch_resume -> scrape_job -> run_scorer

    1. fetch_resume : Fetches the user's resume text from the backend API.
    2. scrape_job   : Fetches and cleans the job info from the given URL.
    3. run_scorer   : Sends the resume + job description to Gemini and returns a structured JSON assessment.

Example usage::
    result = await graph.ainvoke({
        "user_id": "user_id_test",
        "job_url": "https://www.linkedin.com/jobs/view/...",
    })
    score = result["score_result"]
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Dict

import httpx
from dotenv import find_dotenv, load_dotenv
from langgraph.graph import StateGraph

load_dotenv(find_dotenv())
load_dotenv(find_dotenv(".env.local"), override=True)

from agent.scorer import score_resume
from agent.scraper import scrape_job_description

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")


# ── State ─────────────────────────────────────────────────────────────────────


@dataclass
class State:
    """Agent state.

    Attributes:
        user_id: The authenticated user's ID — used to fetch their resume.
        job_url: Full URL of the job posting to analyse.
        resume_text: Populated by fetch_resume; can be pre-filled to skip the fetch.
        job_description: Scraped and cleaned job description (set by scrape_job).
        score_result: Structured JSON assessment from the LLM (set by run_scorer).
    """

    # ── inputs (required at invoke time) ──────────────────────────────────────
    user_id: str = ""
    job_url: str = ""

    # ── populated during execution ────────────────────────────────────────────
    resume_text: str = ""
    job_description: str = ""
    score_result: dict = field(default_factory=dict)


# ── Nodes ─────────────────────────────────────────────────────────────────────


async def fetch_resume(state: State) -> Dict[str, Any]:
    """Fetch the user's latest resume text from the backend."""
    if not state.user_id:
        raise ValueError("user_id is required")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BACKEND_BASE_URL}/users/{state.user_id}/resume")
        resp.raise_for_status()
    data = resp.json()
    if "text" not in data:
        raise ValueError(f"Backend response missing 'text' field: {data}")
    return {"resume_text": data["text"]}


async def scrape_job(state: State) -> Dict[str, Any]:
    """Fetch and clean the job description from the posting URL."""
    jd_text = await asyncio.to_thread(scrape_job_description, state.job_url)
    return {"job_description": jd_text}


async def run_scorer(state: State) -> Dict[str, Any]:
    """Score the resume against the scraped job description."""
    result = await score_resume(
        jd_text=state.job_description,
        resume_text=state.resume_text,
    )
    return {"score_result": result}


# ── Graph ─────────────────────────────────────────────────────────────────────


def create_graph(checkpointer=None):
    """Build and compile the graph.

    Pass a checkpointer for standalone use (e.g. server.py).
    Omit it when running under LangGraph API, which manages persistence itself.
    """
    return (
        StateGraph(State)
        .add_node(fetch_resume)
        .add_node(scrape_job)
        .add_node(run_scorer)
        .add_edge("__start__", "fetch_resume")
        .add_edge("fetch_resume", "scrape_job")
        .add_edge("scrape_job", "run_scorer")
        .compile(name="Resume Scorer", checkpointer=checkpointer)
    )


# LangGraph API entry point — no checkpointer (platform handles persistence)
graph = create_graph()
