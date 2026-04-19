import os

import httpx
from fastapi import APIRouter, HTTPException

from ..src.schemas.user import (
    ScoreRequest,
    ScoreResponse,
    TailorAnswerRequest,
    TailorAnswerResponse,
)

router = APIRouter()

AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8001")


@router.post("/resume/analyze", response_model=ScoreResponse)
async def analyze_resume(body: ScoreRequest) -> ScoreResponse:
    """
    Analyze a resume against a job posting.
    
    Main endpoint for resume scoring. Takes a job URL and analyzes the current user's
    resume against it, returning a structured match analysis.
    
    Request body:
    - **job_url**: URL of the job posting to analyze against
    
    Response:
    - **match_percentage**: 0-100 match score
    - **key_matches**: List of matching skills/experiences
    - **gaps**: List of missing requirements or skills
    - **recommendations**: Suggestions to improve match
    """
    # For now, return mock data while we integrate with the agent
    # In production, this would call the agent service
    return ScoreResponse(
        match_percentage=78.5,
        key_matches=[
            "5+ years of software engineering",
            "Python and FastAPI experience",
            "REST API design",
            "Database optimization",
            "Team leadership experience",
        ],
        gaps=[
            "No explicit Kubernetes experience mentioned",
            "Missing cloud deployment (AWS/GCP) in resume",
            "React experience limited compared to job requirements",
        ],
        recommendations=[
            "Highlight any cloud infrastructure projects you've worked on",
            "Add details about containerization experience",
            "Emphasize frontend optimization work to bridge React gap",
            "Consider adding certifications in cloud platforms",
            "Quantify performance improvements you've achieved",
        ],
    )


@router.post("/generate/answer", response_model=TailorAnswerResponse)
async def generate_tailored_answer(body: TailorAnswerRequest) -> TailorAnswerResponse:
    """
    Generate a tailored interview answer.
    
    Creates a personalized answer to an interview question that combines the user's
    background and experience with the context of the specific job posting.
    
    Request body:
    - **job_url**: URL of the job posting
    - **user_question**: The interview question to answer
    
    Response:
    - **answer**: The generated tailored answer
    - **relevance_score**: 0-100 score indicating how well the answer addresses the question
    """
    # For now, return mock data while we integrate with the agent
    # In production, this would call the agent service
    return TailorAnswerResponse(
        answer=(
            "In my previous role at TechCorp, I led a team of 5 engineers in building a high-availability "
            "microservices platform using Python and FastAPI. We processed over 1M requests daily and maintained "
            "99.9% uptime. I'm excited to bring this expertise to your team and contribute to scaling your platform. "
            "My experience with distributed systems, database optimization, and API design aligns perfectly with "
            "your requirements, and I'm confident I can add immediate value to your engineering team."
        ),
        relevance_score=92.0,
    )
