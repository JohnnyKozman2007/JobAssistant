from supabase import create_client
import os

class Supabase:
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SECRET_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL or SUPABASE_SECRET_KEY are not defined.")
        self.supabase = create_client(url, key)


_instance: Supabase | None = None


def get_db() -> Supabase:
    global _instance
    if _instance is None:
        _instance = Supabase()
    return _instance
    