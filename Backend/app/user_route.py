import os
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from ..database.db_client import Supabase, get_db
from ..helper import Helper
from ..user import User
from ..models import UserCreate, UserUpdate, UserResponse

router = APIRouter()

AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8001")

@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user profile",
    tags=["users"]
)
async def create_user(user: UserCreate, db: Supabase = Depends(get_db)):
    try:
        data = user.dict()
        result = db.create_user(data)
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )
        
        return result.data[0]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Fetch user profile",
    tags=["users"]
)
async def get_user(user_id: str, db: Supabase = Depends(get_db)):
    try:
        result = db.get_user(user_id)
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user profile",
    tags=["users"]
)
async def update_user(
    user_id: str, user: UserUpdate, db: Supabase = Depends(get_db)
):
    try:
        # Check if user exists
        existing = db.get_user(user_id)
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Only update fields that were provided
        data = user.dict(exclude_unset=True)
        
        if not data:
            # If no fields to update, return existing user
            return existing.data[0]
        
        result = db.update_user(user_id, data)
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user",
            )
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user profile",
    tags=["users"]
)
async def delete_user(user_id: str, db: Supabase = Depends(get_db)):
    try:
        # Check if user exists
        existing = db.get_user(user_id)
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        db.delete_user(user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

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

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = None,
    db: Supabase = Depends(get_db)
):
    allowed_types = [
        "application/pdf",
        "application/msword",  # .doc
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # .docx
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and Word documents (.doc, .docx) are allowed"
        )
    if not user_id:
        user_id = str(uuid.uuid4())
    file_path = f"{user_id}/{file.filename}"
    file_bytes = await file.read()

    # Empty file validation
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    existing = db.get_resumes_by_user(user_id)
    if existing.data:
        old_paths: list[str] = [str(r["file_path"]) for r in existing.data if r.get("file_path")]  # type: ignore[union-attr]
        try:
            db.supabase.storage.from_("Resumes").remove(old_paths)
        except Exception:
            pass
        db.delete_resumes_by_user(user_id)

    try:
        db.supabase.storage.from_("Resumes").upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": file.content_type}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")
    try:
        parsed_text = Helper.parse_resume_text(file_bytes, file.content_type)
    except Exception:
        parsed_text = None
    resume_data = {
        "user_id": user_id,
        "file_path": file_path,
        "original_filename": file.filename,
        "mime_type": file.content_type,
        "parsed_text": parsed_text
    }
    try:
        db.insert_resume(resume_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insert failed: {str(e)}")
    return {
        "message": "Upload successful",
        "file_path": file_path,
        "user_id": user_id
    }

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
