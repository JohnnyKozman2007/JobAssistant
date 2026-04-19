from typing import Literal

from agent.state import RequestType, State


def route_request_type(state: State) -> Literal["score_resume", "tailored_answer"]:
    request_type = state.get("request_type")
    if request_type is None:
        raise ValueError("Request type is not defined.")
    if request_type == RequestType.score:
        return "score_resume"
    if request_type == RequestType.question:
        return "tailored_answer"
    raise ValueError(f"Unknown request type: {request_type}")