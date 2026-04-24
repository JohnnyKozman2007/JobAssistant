from supabase import create_client
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()  # Loads API keys from .env file


def _normalize_supabase_url(raw_url: str) -> str:
    """Accept either project URL or REST URL and normalize to project base URL."""
    parsed = urlparse(raw_url.strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return raw_url.rstrip("/")

class Supabase:
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SECRET_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL or SUPABASE_SECRET_KEY are not defined.")
        self.supabase = create_client(_normalize_supabase_url(url), key)

    def insert_resume(self, data: dict):
        """Insert resume metadata into the 'resumes' table."""
        return self.supabase.table("resumes").insert(data).execute()

    def get_resumes_by_user(self, user_id: str):
        return self.supabase.table("resumes").select("file_path").eq("user_id", user_id).execute()

    def delete_resumes_by_user(self, user_id: str):
        return self.supabase.table("resumes").delete().eq("user_id", user_id).execute()
    
    # User management methods
    def create_user(self, data: dict):
        return self.supabase.table("users").insert(data).execute()

    def get_user(self, user_id: str):
        return self.supabase.table("users").select("*").eq("id", user_id).execute()

    def update_user(self, user_id: str, data: dict):
        return self.supabase.table("users").update(data).eq("id", user_id).execute()

    def delete_user(self, user_id: str):
        return self.supabase.table("users").delete().eq("id", user_id).execute()

    # Profile management methods
    def create_profile(self, data: dict):
        return self.supabase.table("profiles").insert(data).execute()

    def get_profile_by_user(self, user_id: str):
        return self.supabase.table("profiles").select("*").eq("user_id", user_id).execute()

    def update_profile(self, profile_id: str, data: dict):
        return self.supabase.table("profiles").update(data).eq("id", profile_id).execute()

    def delete_profile(self, profile_id: str):
        return self.supabase.table("profiles").delete().eq("id", profile_id).execute()

_instance: Supabase | None = None

def get_db() -> Supabase:
    global _instance
    if _instance is None:
        _instance = Supabase()
    return _instance