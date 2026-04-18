from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from .database.db_client import Supabase


class User:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.resume_bucket = os.getenv("SUPABASE_RESUME_BUCKET")

    def get_latest_resume(self, db: Supabase) -> tuple[str | None, bytes | None, str | None]:
        storage = db.client.storage.from_(self._resolve_resume_bucket(db))
        candidates = self._list_candidates(storage)
        if not candidates:
            return None, None, None

        latest = self._pick_latest(candidates)
        file_name = latest.get("full_path") or latest.get("name")
        if not file_name:
            return None, None, None

        file_bytes = storage.download(file_name)
        return file_name, file_bytes, self._guess_mimetype(file_name)

    def _resolve_resume_bucket(self, db: Supabase) -> str:
        if self.resume_bucket:
            return self.resume_bucket

        try:
            buckets = db.client.storage.list_buckets()
        except Exception:
            return "resumes"

        for bucket in buckets:
            name = bucket.get("name") if isinstance(bucket, dict) else getattr(bucket, "name", None)
            if isinstance(name, str) and name.lower() == "resumes":
                return name

        return "resumes"

    def _list_candidates(self, storage: Any) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen_paths: set[str] = set()

        # Support both "<user_id>/file.pdf" and root-level naming conventions.
        for prefix in (self.user_id, f"{self.user_id}/", ""):
            try:
                listed = storage.list(prefix)
            except Exception:
                continue
            if not isinstance(listed, list):
                continue
            for item in listed:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if not isinstance(name, str) or not name:
                    continue
                if not self._is_resume_candidate(item):
                    continue
                if not prefix and not self._belongs_to_user(name):
                    continue
                full_path = f"{prefix.rstrip('/')}/{name}".lstrip("/")
                if full_path in seen_paths:
                    continue
                seen_paths.add(full_path)
                items.append({**item, "full_path": full_path})
        return items

    def _is_resume_candidate(self, item: dict[str, Any]) -> bool:
        name = str(item.get("name", "")).strip()
        if not name or name.startswith("."):
            return False

        lowered = name.lower()
        if lowered.endswith((".pdf", ".docx", ".doc", ".txt")):
            return True

        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            mimetype = metadata.get("mimetype")
            if isinstance(mimetype, str):
                mt = mimetype.lower()
                if "pdf" in mt or "word" in mt or "officedocument" in mt or mt == "text/plain":
                    return True

        return False

    def _belongs_to_user(self, name: str) -> bool:
        lowered_name = name.lower()
        lowered_user_id = self.user_id.lower()
        return (
            lowered_name.startswith(f"{lowered_user_id}.")
            or lowered_name.startswith(f"{lowered_user_id}_")
            or lowered_name.startswith(f"{lowered_user_id}-")
        )

    def _pick_latest(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        def key(item: dict[str, Any]) -> datetime:
            for field in ("updated_at", "created_at", "last_accessed_at"):
                raw = item.get(field)
                if not raw or not isinstance(raw, str):
                    continue
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    continue
            return datetime.min

        return max(items, key=key)

    def _guess_mimetype(self, file_name: str) -> str:
        lowered = file_name.lower()
        if lowered.endswith(".pdf"):
            return "application/pdf"
        if lowered.endswith(".docx"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if lowered.endswith(".doc"):
            return "application/msword"
        if lowered.endswith(".txt"):
            return "text/plain"
        return "application/octet-stream"
