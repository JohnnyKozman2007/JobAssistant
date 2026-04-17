from fastapi import APIRouter, HTTPException
from Backend.database.db_client import Supabase
from Backend.user import User
from Backend.helper import Helper

router = APIRouter()


@router.get("/{user_id}/resume")
def get_resume_text(user_id: str):
    db = Supabase()
    user = User(user_id)
    file_name, file_bytes = user.get_latest_resume_pdf_bytes(db)
    if not file_name or not file_bytes:
        raise HTTPException(status_code=404, detail="No resume found for this user.")
    return {"text": Helper.parse_resume_text(file_name, file_bytes)}
