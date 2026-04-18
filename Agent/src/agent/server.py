"""FastAPI server exposing the Resume Scorer agent over HTTP."""

from __future__ import annotations

import logging

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException

logger = logging.getLogger(__name__)
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

from agent.graph import State, create_graph

load_dotenv(find_dotenv())

app = FastAPI(title="Resume Scorer Agent")

# Standalone server: compile with MemorySaver so sessions are persisted per user
graph = create_graph(checkpointer=MemorySaver())


class ScoreRequest(BaseModel):
    job_url: str


@app.post("/score")
async def score(user_id: str, body: ScoreRequest):
    """Score the user's saved resume against the given job posting."""
    config = {"configurable": {"thread_id": user_id}}
    try:
        result = await graph.ainvoke(
            State(user_id=user_id, job_url=body.job_url),
            config=config,
        )
    except Exception as e:
        logger.exception("Score request failed for user %s", user_id)
        raise HTTPException(status_code=500, detail=str(e))
    return result["score_result"]


@app.get("/health")
def health():
    return {"status": "ok"}
