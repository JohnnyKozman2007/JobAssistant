import os
from datetime import datetime
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from ..database.db_client import Supabase, get_db
from ..helper import Helper
from ..user import User
from ..src.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    ScoreRequest as ScoreRequestSchema,
    TailorAnswerRequest as TailorAnswerRequestSchema,
    ResumeResponse,
    ScoreResponse,
    TailorAnswerResponse,
)


router = APIRouter()

AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8001")


# Keep backward compatibility with existing schemas
class ScoreRequest(BaseModel):
    job_url: str


class TailorAnswerRequest(BaseModel):
    job_url: str
    user_question: str


@router.get("/{user_id}/resume")
def get_resume_text(user_id: str, db: Supabase = Depends(get_db)):
    user = User(user_id)
    file_name, file_bytes, mimetype = user.get_latest_resume(db)
    if not file_name or not file_bytes or not mimetype:
        raise HTTPException(status_code=404, detail="No resume found for this user.")
    try:
        return {"text": Helper.parse_resume_text(file_bytes, mimetype)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


def _normalize_user_row(user_row: dict) -> UserResponse:
    return UserResponse(**user_row)


def _get_user_or_404(user_id: str, db: Supabase) -> dict:
    response = db.get_user(user_id)
    user_rows = response.data or []
    if not user_rows:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found.")
    return user_rows[0]

# User profile endpoints
@router.post("", response_model=UserResponse)
def create_user(user_data: UserCreate, db: Supabase = Depends(get_db)) -> UserResponse:
    """Create a new user profile."""
    user_id = str(uuid4())
    now = datetime.utcnow()
    user_payload = {
        "user_id": user_id,
        "email": user_data.email,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "phone_number": user_data.phone_number,
        "location": user_data.location,
        "desired_job_title": user_data.desired_job_title,
        "years_of_experience": user_data.years_of_experience,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "has_resume": False,
    }

    try:
        response = db.insert_user(user_payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {exc}")

    created_rows = response.data or []
    if not created_rows:
        raise HTTPException(status_code=500, detail="User was not created.")

    return _normalize_user_row(created_rows[0])

# Get and update user profile endpoints
@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Supabase = Depends(get_db)) -> UserResponse:
    """Fetch a user profile by ID."""
    user_data = _get_user_or_404(user_id, db)
    return _normalize_user_row(user_data)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, user_data: UserUpdate, db: Supabase = Depends(get_db)) -> UserResponse:
    """Update a user profile."""
    update_data = user_data.model_dump(exclude_unset=True)
    if not update_data:
        return _normalize_user_row(_get_user_or_404(user_id, db))

    update_data["updated_at"] = datetime.utcnow().isoformat()

    try:
        response = db.update_user(user_id, update_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update user: {exc}")

    updated_rows = response.data or []
    if not updated_rows:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found.")

    return _normalize_user_row(updated_rows[0])


# Resume upload and update endpoints
@router.post("/{user_id}/resume", response_model=ResumeResponse)
async def upload_resume(user_id: str, file: UploadFile = File(...), db: Supabase = Depends(get_db)) -> ResumeResponse:
    """Upload and store a resume file for a user."""
    _get_user_or_404(user_id, db)
    
    # Validate file type
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid file type. Allowed types: PDF, DOCX, DOC, TXT"
        )
    
    # Mock resume storage
    resume_response = ResumeResponse(
        filename=file.filename or "resume",
        uploaded_at=datetime.utcnow(),
        mimetype=file.content_type,
    )

    try:
        db.update_user(user_id, {"has_resume": True, "updated_at": datetime.utcnow().isoformat()})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update user resume flag: {exc}")
    
    return resume_response


@router.put("/{user_id}/resume", response_model=ResumeResponse)
async def update_resume(user_id: str, file: UploadFile = File(...), db: Supabase = Depends(get_db)) -> ResumeResponse:
    """Update a user's resume file."""
    _get_user_or_404(user_id, db)
    
    # Validate file type
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid file type. Allowed types: PDF, DOCX, DOC, TXT"
        )
    
    # Mock resume update
    resume_response = ResumeResponse(
        filename=file.filename or "resume",
        uploaded_at=datetime.utcnow(),
        mimetype=file.content_type,
    )
    
    return resume_response



# User-specific scoring and answer generation endpoints
@router.post("/{user_id}/score")
async def score_resume(user_id: str, body: ScoreRequest):
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(
                f"{AGENT_BASE_URL}/score",
                params={"user_id": user_id},
                json={"job_url": body.job_url},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Agent error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Agent unreachable: {e}")
    return response.json()

@router.post("/{user_id}/answer")
async def tailor_answer(user_id: str, body: TailorAnswerRequest):
    """Forward the tailored answer request to the agent."""
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(
                f"{AGENT_BASE_URL}/answer",
                params={"user_id": user_id},
                json={"job_url": body.job_url, "user_question": body.user_question},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Agent error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Agent unreachable: {e}")

    return response.json()
