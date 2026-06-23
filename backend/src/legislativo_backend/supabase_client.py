from __future__ import annotations

import logging
import os
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 1.5


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

    def _upsert(self, table: str, rows: list[dict[str, Any]], on_conflict: str = "source,external_id", retries: int = MAX_RETRIES) -> int:
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
        for attempt in range(1, retries + 1):
            try:
                response = client.table(table).upsert(deduped, on_conflict=on_conflict).execute()
                if hasattr(response, "error") and response.error:
                    raise RuntimeError(f"Supabase upsert error on {table}: {response.error}")
                return len(response.data) if response.data else 0
            except Exception:
                if attempt == retries:
                    raise
                logger.warning(
                    "Supabase upsert attempt %d/%d failed for table %s, retrying...",
                    attempt, retries, table, exc_info=True,
                )
                time.sleep(RETRY_BACKOFF * (2 ** (attempt - 1)))
        return 0

    def upsert_raw_payload(self, source: str, kind: str, external_id: str, payload: dict[str, Any]) -> int:
        if not self._enabled:
            return 0
        from datetime import UTC, datetime
        row = {
            "source": source,
            "kind": kind,
            "external_id": external_id,
            "payload_json": payload,
            "collected_at": datetime.now(UTC).isoformat(),
        }
        return self._upsert("raw_payloads", [row], on_conflict="source,kind,external_id")

    def record_sync_run(
        self,
        job: str,
        source: str,
        status: str,
        records_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self._enabled:
            return
        from datetime import UTC, datetime
        now = datetime.now(UTC).isoformat()
        client = self._get_client()
        client.table("sync_runs").insert({
            "job": job,
            "source": source,
            "status": status,
            "started_at": now,
            "finished_at": now,
            "records_count": records_count,
            "metadata_json": metadata or {},
        }).execute()

    def refresh_materialized_views(self) -> None:
        if not self._enabled:
            return
        client = self._get_client()
        for view in ["parlamentar_kpis", "despesas_por_categoria", "proposition_ultimo_status"]:
            try:
                client.rpc("refresh_view", {"view_name": view}).execute()
            except Exception:
                logger.debug("refresh_materialized_views via RPC falhou para %s, tentando SQL direto", view)
                try:
                    sql = f"REFRESH MATERIALIZED VIEW {view}"
                    client.rpc("exec_sql", {"query": sql}).execute()
                except Exception:
                    logger.warning("Nao foi possivel refrescar materialized view %s", view, exc_info=True)

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

    def upsert_discursos(self, rows: list[dict[str, Any]]) -> int:
        return self._upsert("discursos", rows, on_conflict="senador_codigo,data_discurso")
