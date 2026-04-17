from fastapi import APIRouter, Depends, HTTPException
from Backend.database.db_client import Supabase, get_db
from Backend.user import User
from Backend.helper import Helper

router = APIRouter()


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
