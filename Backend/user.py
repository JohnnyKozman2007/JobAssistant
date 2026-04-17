from Backend.database.db_client import Supabase

class User:
    BUCKET_NAME = "Resumes"
    SUPPORTED_RESUME_FILE_TYPE = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",]
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
    
    def get_latest_resume_pdf_bytes(self, db: Supabase):
        files = db.supabase.storage.from_(self.BUCKET_NAME).list(self.user_id)

        files = [
            f for f in files
            if f.get("metadata", {}).get("mimetype") in self.SUPPORTED_RESUME_FILE_TYPE
        ]

        latest = max(files, key=lambda f: f["created_at"], default=None)
        if not latest:
            return None, None

        file_name = latest["name"]
        file_bytes = db.supabase.storage.from_(self.BUCKET_NAME).download(file_name)
        return file_name, file_bytes
        