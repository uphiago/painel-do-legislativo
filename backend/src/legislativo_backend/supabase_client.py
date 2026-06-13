from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class SupabaseClient:
    def __init__(self) -> None:
        self._url = os.getenv("SUPABASE_URL", "")
        self._key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self._enabled = bool(self._url and self._key)
        self._client: Any = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from supabase import create_client

            self._client = create_client(self._url, self._key)
        except ImportError:
            raise RuntimeError(
                "supabase-py not installed. Run: uv add supabase"
            )
        return self._client

    def _upsert(self, table: str, rows: list[dict[str, Any]], on_conflict: str = "source,external_id") -> int:
        if not rows:
            return 0
        seen: set[tuple] = set()
        deduped: list[dict[str, Any]] = []
        conflict_cols = [c.strip() for c in on_conflict.split(",")]
        for row in rows:
            key = tuple(str(row.get(c, "")) for c in conflict_cols)
            if key not in seen:
                seen.add(key)
                deduped.append(row)
        if not deduped:
            return 0
        client = self._get_client()
        response = client.table(table).upsert(deduped, on_conflict=on_conflict).execute()
        if hasattr(response, "error") and response.error:
            raise RuntimeError(f"Supabase upsert error on {table}: {response.error}")
        return len(response.data) if response.data else 0

    def upsert_parlamentarians(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("parlamentarians", rows)

    def upsert_propositions(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("propositions", rows)

    def upsert_expenses(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("expenses", rows)

    def upsert_parties(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("parties", rows)

    def upsert_legislatures(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("legislatures", rows)

    def upsert_organs(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("organs", rows)

    def upsert_mandates(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("parliamentarian_mandates", rows,
                            on_conflict="parliamentarian_external_id,source,legislature_id")

    def upsert_organ_memberships(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("organ_memberships", rows,
                            on_conflict="parliamentarian_external_id,source,organ_external_id,data_inicio")

    def upsert_frentes(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("parliamentary_fronts", rows, on_conflict="external_id")

    def upsert_front_memberships(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("front_memberships", rows,
                            on_conflict="front_external_id,parliamentarian_external_id")

    def upsert_proposition_authors(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("proposition_authors", rows,
                            on_conflict="proposition_source,proposition_external_id,author_name,signature_order")

    def upsert_proposition_themes(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("proposition_themes", rows,
                            on_conflict="proposition_source,proposition_external_id,theme_code")

    def upsert_proposition_trackings(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("proposition_trackings", rows,
                            on_conflict="proposition_source,proposition_external_id,sequencia")

    def upsert_proposition_types(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("proposition_types", rows, on_conflict="codigo")
