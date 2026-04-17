from supabase import create_client
import os

class Supabase:
    def __init__(self) -> None:
        if not Supabase._check_env_var():
            raise ValueError("SUPABASE_URL or SUPABASE_SECRET_KEY are not defined.")

        self.supabase = create_client(
            os.getenv("SUPABASE_URL"), # type: ignore
            os.getenv("SUPABASE_SECRET_KEY") # type: ignore
        )

    @staticmethod
    def _check_env_var():
        if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SECRET_KEY"):
            return True
        return False