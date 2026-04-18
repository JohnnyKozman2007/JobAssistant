from __future__ import annotations

import os

from supabase import Client, create_client


class Supabase:
    """Small wrapper around the Supabase client used by the API routes."""

    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SECRET_KEY")

        if not url or not service_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SECRET_KEY must be configured.")

        self.client: Client = create_client(url, service_key)


def get_db() -> Supabase:
    return Supabase()
