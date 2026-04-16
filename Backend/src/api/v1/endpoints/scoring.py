"""Resume Scoring Endpoint - Score resume against job description."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1", tags=["scoring"])


class ScoreResumeRequest(BaseModel):
    """Request body for resume scoring."""
    job_url: str = Field(..., description="URL of the job listing")
    resume_text: str = Field(..., description="Full text content of the resume")


class Improvement(BaseModel):
    """Improvement suggestion for resume."""
    item: str
    priority: str = Field(..., pattern="^(high|medium|low)$")
    reason: str


class ScoreResumeResponse(BaseModel):
    """Response for resume scoring endpoint."""
    match_score: float = Field(..., ge=0, le=100, description="Match score 0-100")
    skills: list[str] = Field(default_factory=list, description="Matched skills")
    improvements: list[Improvement] = Field(default_factory=list, description="Suggestions")
    summary: str = Field(..., description="Summary of the match")


@router.post("/score-resume", response_model=ScoreResumeResponse, status_code=status.HTTP_200_OK)
async def score_resume(request: ScoreResumeRequest) -> ScoreResumeResponse:
    """
    Score a resume against a job description.
    
    **Parameters:**
    - `job_url`: URL of the job listing to analyze
    - `resume_text`: Full text content of the candidate's resume
    
    **Returns:**
    - `match_score`: Percentage match (0-100)
    - `skills`: List of matched skills
    - `improvements`: List of suggested improvements
    - `summary`: Overall assessment
    
    **Errors:**
    - 422: Invalid request body
    - 500: Internal server error
    """
    try:
        # TODO: Integrate with ScoringService
        # scoring_service = ScoringService()
        # result = await scoring_service.score_resume(request.job_url, request.resume_text)
        
        # Placeholder response
        return ScoreResumeResponse(
            match_score=0.0,
            skills=[],
            improvements=[],
            summary="Scoring endpoint placeholder"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scoring resume: {str(e)}"
        )
