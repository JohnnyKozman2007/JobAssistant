import os
from typing import Any

from supabase import create_client

class Supabase:
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SECRET_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL or SUPABASE_SECRET_KEY are not defined.")
        self.supabase = create_client(url, key)

    def insert_user(self, data: dict[str, Any]):
        """Insert a user profile into the users table."""
        return self.supabase.table("users").insert(data).execute()

    def get_user(self, user_id: str):
        """Fetch a user profile by user_id."""
        return self.supabase.table("users").select("*").eq("user_id", user_id).execute()

    def update_user(self, user_id: str, data: dict[str, Any]):
        """Update a user profile by user_id."""
        return self.supabase.table("users").update(data).eq("user_id", user_id).execute()

    def insert_resume(self, data: dict):
        """Insert resume metadata into the 'resumes' table."""
        return self.supabase.table("resumes").insert(data).execute()

_instance: Supabase | None = None

def get_db() -> Supabase:
    global _instance
    if _instance is None:
        _instance = Supabase()
    return _instance