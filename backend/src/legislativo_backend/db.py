from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from legislativo_backend.normalizers import DespesaResumo, ParlamentarResumo, ProposicaoResumo
from legislativo_backend.storage import project_root


def default_db_path() -> Path:
    return project_root() / "data" / "local" / "painel.db"


class LocalDatabase:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else default_db_path()

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def summary(self) -> dict[str, int]:
        tables = [
            "parlamentarians", "propositions", "expenses", "raw_payloads", "sync_runs",
            "parties", "legislatures", "organs", "parliamentarian_mandates",
            "organ_memberships", "parliamentary_fronts", "front_memberships",
            "proposition_types", "proposition_authors", "proposition_themes",
            "proposition_trackings",
        ]
        with self.connect() as connection:
            return {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in tables
            }

    def list_parliamentarians(
        self,
        *,
        source: str,
        limit: int,
        offset: int = 0,
    ) -> list[dict[str, str]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT external_id, nome
                FROM parlamentarians
                WHERE source = ?
                ORDER BY nome
                LIMIT ? OFFSET ?
                """,
                (source, limit, offset),
            ).fetchall()
        return [{"external_id": row["external_id"], "name": row["nome"]} for row in rows]

    def list_propositions(
        self,
        *,
        source: str,
        limit: int,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT external_id, sigla, numero, ano
                FROM propositions
                WHERE source = ?
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (source, limit, offset),
            ).fetchall()
        return [
            {
                "external_id": row["external_id"],
                "sigla": row["sigla"],
                "numero": row["numero"],
                "ano": row["ano"],
            }
            for row in rows
        ]

    def coverage(self) -> dict[str, int]:
        with self.connect() as connection:
            camara_parliamentarians = _scalar(
                connection,
                "SELECT COUNT(*) FROM parlamentarians WHERE source = 'camara'",
            )
            senado_parliamentarians = _scalar(
                connection,
                "SELECT COUNT(*) FROM parlamentarians WHERE source = 'senado'",
            )
            camara_profiles = _scalar(
                connection,
                """
                SELECT COUNT(DISTINCT external_id)
                FROM raw_payloads
                WHERE source = 'camara' AND kind = 'deputado-perfil'
                """,
            )
            senado_profiles = _scalar(
                connection,
                """
                SELECT COUNT(DISTINCT external_id)
                FROM raw_payloads
                WHERE source = 'senado' AND kind IN ('senador-processos', 'senador-error')
                """,
            )
        return {
            "camara_parlamentarians": camara_parliamentarians,
            "senado_parliamentarians": senado_parliamentarians,
            "camara_profiles": camara_profiles,
            "senado_profiles": senado_profiles,
        }

    def upsert_parlamentarians(self, rows: list[ParlamentarResumo]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO parlamentarians (
                  source, external_id, nome, casa, partido, uf, email, foto_url, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, external_id) DO UPDATE SET
                  nome = excluded.nome,
                  casa = excluded.casa,
                  partido = excluded.partido,
                  uf = excluded.uf,
                  email = excluded.email,
                  foto_url = excluded.foto_url,
                  updated_at = excluded.updated_at
                """,
                [
                    (
                        row.source,
                        row.external_id,
                        row.nome,
                        row.casa,
                        row.partido,
                        row.uf,
                        row.email,
                        row.foto_url,
                        now,
                    )
                    for row in rows
                ],
            )
        return len(rows)

    def get_enriched_parliamentarian_ids(self, source: str) -> set[str]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT external_id FROM raw_payloads WHERE source = ? AND kind = ?",
                (source, "deputado-full" if source == "camara" else "senador-full"),
            ).fetchall()
        return {row["external_id"] for row in rows}

    def list_unenriched_propositions(
        self,
        source: str = "camara",
        limit: int = 100,
        offset: int = 0,
        min_ano: int | None = None,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT p.external_id, p.ano, p.sigla, p.numero
            FROM propositions p
            WHERE p.source = ?
              AND p.external_id NOT IN (
                SELECT external_id FROM raw_payloads WHERE source = ? AND kind = 'proposicao-full'
              )
        """
        params: list[Any] = [source, source]
        if min_ano is not None:
            query += "  AND p.ano >= ?"
            params.append(min_ano)
        query += " ORDER BY p.ano DESC, p.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [{"external_id": row["external_id"], "ano": row["ano"],
                 "sigla": row["sigla"], "numero": row["numero"]} for row in rows]

    def count_unenriched_propositions(self, source: str = "camara", min_ano: int | None = None) -> int:
        query = """
            SELECT COUNT(*)
            FROM propositions p
            WHERE p.source = ?
              AND p.external_id NOT IN (
                SELECT external_id FROM raw_payloads WHERE source = ? AND kind = 'proposicao-full'
              )
        """
        params: list[Any] = [source, source]
        if min_ano is not None:
            query += "  AND p.ano >= ?"
            params.append(min_ano)
        with self.connect() as connection:
            return int(connection.execute(query, tuple(params)).fetchone()[0])

    def list_recent_sync_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT job, source, status, started_at, finished_at, records_count"
                " FROM sync_runs ORDER BY id DESC LIMIT ?", (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def upsert_propositions(self, rows: list[ProposicaoResumo]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO propositions (
                  source, external_id, casa, sigla, numero, ano, ementa,
                  data_apresentacao, autor_principal, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, external_id) DO UPDATE SET
                  casa = excluded.casa,
                  sigla = excluded.sigla,
                  numero = excluded.numero,
                  ano = excluded.ano,
                  ementa = excluded.ementa,
                  data_apresentacao = excluded.data_apresentacao,
                  autor_principal = excluded.autor_principal,
                  updated_at = excluded.updated_at
                """,
                [
                    (
                        row.source,
                        row.external_id,
                        row.casa,
                        row.sigla,
                        row.numero,
                        row.ano,
                        row.ementa,
                        row.data_apresentacao,
                        _bool_to_int(row.autor_principal),
                        now,
                    )
                    for row in rows
                ],
            )
        return len(rows)

    def upsert_expenses(self, rows: list[DespesaResumo]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO expenses (
                  source, external_id, parlamentar_external_id, parlamentar_nome,
                  ano, mes, categoria, fornecedor, documento, data, valor, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, external_id) DO UPDATE SET
                  parlamentar_external_id = excluded.parlamentar_external_id,
                  parlamentar_nome = excluded.parlamentar_nome,
                  ano = excluded.ano,
                  mes = excluded.mes,
                  categoria = excluded.categoria,
                  fornecedor = excluded.fornecedor,
                  documento = excluded.documento,
                  data = excluded.data,
                  updated_at = excluded.updated_at
                """,
                [
                    (
                        row.source,
                        row.external_id,
                        row.parlamentar_external_id,
                        row.parlamentar_nome,
                        row.ano,
                        row.mes,
                        row.categoria,
                        row.fornecedor,
                        row.documento,
                        row.data,
                        row.valor,
                        now,
                    )
                    for row in rows
                ],
            )
        return len(rows)

    def upsert_raw_payload(
        self,
        *,
        source: str,
        kind: str,
        external_id: str,
        payload: dict[str, Any] | list[Any],
    ) -> None:
        now = _now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO raw_payloads (source, kind, external_id, payload_json, collected_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, kind, external_id) DO UPDATE SET
                  payload_json = excluded.payload_json,
                  collected_at = excluded.collected_at
                """,
                (source, kind, external_id, json.dumps(payload, ensure_ascii=False), now),
            )

    def record_sync_run(
        self,
        *,
        job: str,
        source: str,
        status: str,
        records_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = _now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO sync_runs (
                  job, source, status, started_at, finished_at, records_count, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job,
                    source,
                    status,
                    now,
                    now,
                    records_count,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )


    def upsert_parties(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO parties (source, external_id, sigla, nome, logo_url, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source, external_id) DO UPDATE SET
                     sigla = excluded.sigla, nome = excluded.nome,
                     logo_url = excluded.logo_url, updated_at = excluded.updated_at""",
                [(r.get("source", "camara"), r["external_id"], r["sigla"], r.get("nome"),
                  r.get("logo_url"), now) for r in rows],
            )
        return len(rows)

    def upsert_legislatures(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO legislatures (source, external_id, numero, data_inicio, data_fim, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source, external_id) DO UPDATE SET
                     numero = excluded.numero, data_inicio = excluded.data_inicio,
                     data_fim = excluded.data_fim, updated_at = excluded.updated_at""",
                [(r.get("source", "camara"), r["external_id"], r.get("numero"),
                  r.get("data_inicio"), r.get("data_fim"), now) for r in rows],
            )
        return len(rows)

    def upsert_organs(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO organs (source, external_id, sigla, nome, tipo, casa, data_inicio, data_fim, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source, external_id) DO UPDATE SET
                     sigla = excluded.sigla, nome = excluded.nome, tipo = excluded.tipo,
                     casa = excluded.casa, data_inicio = excluded.data_inicio,
                     data_fim = excluded.data_fim, updated_at = excluded.updated_at""",
                [(r["source"], r["external_id"], r.get("sigla"), r.get("nome"),
                  r.get("tipo"), r.get("casa"), r.get("data_inicio"), r.get("data_fim"), now)
                 for r in rows],
            )
        return len(rows)

    def upsert_mandates(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO parliamentarian_mandates
                   (parlamentar_external_id, source, legislature_id, party_sigla, uf,
                    status, condition, data_inicio, data_fim, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(parlamentar_external_id, source, legislature_id) DO UPDATE SET
                     party_sigla = excluded.party_sigla, uf = excluded.uf,
                     status = excluded.status, condition = excluded.condition,
                     data_inicio = excluded.data_inicio, data_fim = excluded.data_fim,
                     updated_at = excluded.updated_at""",
                [(r["parlamentar_external_id"], r["source"], r.get("legislature_id"),
                  r.get("party_sigla"), r.get("uf"), r.get("status"), r.get("condition"),
                  r.get("data_inicio"), r.get("data_fim"), now) for r in rows],
            )
        return len(rows)

    def upsert_organ_memberships(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO organ_memberships
                   (parlamentar_external_id, source, organ_external_id, role,
                    data_inicio, data_fim, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(parlamentar_external_id, source, organ_external_id, data_inicio)
                   DO UPDATE SET
                     role = excluded.role, data_fim = excluded.data_fim,
                     updated_at = excluded.updated_at""",
                [(r["parlamentar_external_id"], r["source"], r["organ_external_id"],
                  r.get("role"), r.get("data_inicio"), r.get("data_fim"), now) for r in rows],
            )
        return len(rows)

    def upsert_frentes(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO parliamentary_fronts (external_id, titulo, legislature_id, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(external_id) DO UPDATE SET
                     titulo = excluded.titulo, legislature_id = excluded.legislature_id,
                     updated_at = excluded.updated_at""",
                [(r["external_id"], r.get("titulo"), r.get("legislature_id"), now) for r in rows],
            )
        return len(rows)

    def upsert_front_memberships(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO front_memberships
                   (front_external_id, parlamentar_external_id, legislature_id, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(front_external_id, parlamentar_external_id) DO UPDATE SET
                     legislature_id = excluded.legislature_id, updated_at = excluded.updated_at""",
                [(r["front_external_id"], r["parlamentar_external_id"],
                  r.get("legislature_id"), now) for r in rows],
            )
        return len(rows)

    def upsert_proposition_authors(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO proposition_authors
                   (proposition_source, proposition_external_id, parlamentar_external_id,
                    author_name, author_type, signature_order, proponent, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(proposition_source, proposition_external_id, author_name, signature_order)
                   DO UPDATE SET
                     parlamentar_external_id = excluded.parlamentar_external_id,
                     author_type = excluded.author_type, proponent = excluded.proponent,
                     updated_at = excluded.updated_at""",
                [(r["proposition_source"], r["proposition_external_id"],
                  r.get("parlamentar_external_id"), r.get("author_name"),
                  r.get("author_type"), r.get("signature_order"), r.get("proponent", 0), now)
                 for r in rows],
            )
        return len(rows)

    def upsert_proposition_themes(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO proposition_themes
                   (proposition_source, proposition_external_id, theme_code, theme_name, relevance, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(proposition_source, proposition_external_id, theme_code) DO UPDATE SET
                     theme_name = excluded.theme_name, relevance = excluded.relevance,
                     updated_at = excluded.updated_at""",
                [(r["proposition_source"], r["proposition_external_id"], r.get("theme_code"),
                  r.get("theme_name"), r.get("relevance", 0), now) for r in rows],
            )
        return len(rows)

    def upsert_proposition_trackings(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO proposition_trackings
                   (proposition_source, proposition_external_id, sequencia, data_hora,
                    orgao_sigla, orgao_id, descricao_tramitacao, codigo_tipo_tramitacao,
                    descricao_situacao, codigo_situacao, despacho, url, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(proposition_source, proposition_external_id, sequencia) DO UPDATE SET
                     data_hora = excluded.data_hora, orgao_sigla = excluded.orgao_sigla,
                     orgao_id = excluded.orgao_id, descricao_tramitacao = excluded.descricao_tramitacao,
                     codigo_tipo_tramitacao = excluded.codigo_tipo_tramitacao,
                     descricao_situacao = excluded.descricao_situacao,
                     codigo_situacao = excluded.codigo_situacao, despacho = excluded.despacho,
                     url = excluded.url, updated_at = excluded.updated_at""",
                [(r["proposition_source"], r["proposition_external_id"], r.get("sequencia"),
                  r.get("data_hora"), r.get("orgao_sigla"), r.get("orgao_id"),
                  r.get("descricao_tramitacao"), r.get("codigo_tipo_tramitacao"),
                  r.get("descricao_situacao"), r.get("codigo_situacao"), r.get("despacho"),
                  r.get("url"), now) for r in rows],
            )
        return len(rows)

    def upsert_proposition_types(self, rows: list[dict[str, Any]]) -> int:
        now = _now()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO proposition_types (codigo, sigla, nome, descricao, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(codigo) DO UPDATE SET
                     sigla = excluded.sigla, nome = excluded.nome,
                     descricao = excluded.descricao, updated_at = excluded.updated_at""",
                [(r["codigo"], r.get("sigla"), r.get("nome"), r.get("descricao"), now) for r in rows],
            )
        return len(rows)

    def insert_propositions_bulk(self, rows: list[ProposicaoResumo]) -> int:
        now = _now()
        with self.connect() as connection:
            cursor = connection.executemany(
                """INSERT OR IGNORE INTO propositions
                   (source, external_id, casa, sigla, numero, ano, ementa,
                    data_apresentacao, autor_principal, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        row.source, row.external_id, row.casa, row.sigla,
                        row.numero, row.ano, row.ementa,
                        row.data_apresentacao, _bool_to_int(row.autor_principal), now,
                    )
                    for row in rows
                ],
            )
        return cursor.rowcount


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _scalar(connection: sqlite3.Connection, query: str) -> int:
    return int(connection.execute(query).fetchone()[0])


def _bool_to_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job TEXT NOT NULL,
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT NOT NULL,
  records_count INTEGER NOT NULL DEFAULT 0,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS parlamentarians (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  nome TEXT NOT NULL,
  casa TEXT NOT NULL,
  partido TEXT,
  uf TEXT,
  email TEXT,
  foto_url TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS propositions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  casa TEXT NOT NULL,
  sigla TEXT,
  numero TEXT,
  ano INTEGER,
  ementa TEXT,
  data_apresentacao TEXT,
  autor_principal INTEGER,
  updated_at TEXT NOT NULL,
  UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  parlamentar_external_id TEXT,
  parlamentar_nome TEXT,
  ano INTEGER,
  mes INTEGER,
  categoria TEXT,
  fornecedor TEXT,
  documento TEXT,
  data TEXT,
  valor REAL NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS raw_payloads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  kind TEXT NOT NULL,
  external_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  collected_at TEXT NOT NULL,
  UNIQUE(source, kind, external_id)
);

-- New tables for enriched data model

CREATE TABLE IF NOT EXISTS parties (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL DEFAULT 'camara',
  external_id TEXT NOT NULL,
  sigla TEXT NOT NULL,
  nome TEXT,
  logo_url TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS legislatures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL DEFAULT 'camara',
  external_id TEXT NOT NULL,
  numero INTEGER,
  data_inicio TEXT,
  data_fim TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS organs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  sigla TEXT,
  nome TEXT,
  tipo TEXT,
  casa TEXT,
  data_inicio TEXT,
  data_fim TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS parliamentarian_mandates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  parlamentar_external_id TEXT NOT NULL,
  source TEXT NOT NULL,
  legislature_id TEXT,
  party_sigla TEXT,
  uf TEXT,
  status TEXT,
  condition TEXT,
  data_inicio TEXT,
  data_fim TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE(parlamentar_external_id, source, legislature_id)
);

CREATE TABLE IF NOT EXISTS organ_memberships (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  parlamentar_external_id TEXT NOT NULL,
  source TEXT NOT NULL,
  organ_external_id TEXT NOT NULL,
  role TEXT,
  data_inicio TEXT,
  data_fim TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE(parlamentar_external_id, source, organ_external_id, data_inicio)
);

CREATE TABLE IF NOT EXISTS parliamentary_fronts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  external_id TEXT NOT NULL,
  titulo TEXT,
  legislature_id INTEGER,
  updated_at TEXT NOT NULL,
  UNIQUE(external_id)
);

CREATE TABLE IF NOT EXISTS front_memberships (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  front_external_id TEXT NOT NULL,
  parlamentar_external_id TEXT NOT NULL,
  legislature_id INTEGER,
  updated_at TEXT NOT NULL,
  UNIQUE(front_external_id, parlamentar_external_id)
);

CREATE TABLE IF NOT EXISTS proposition_types (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo TEXT NOT NULL UNIQUE,
  sigla TEXT,
  nome TEXT,
  descricao TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proposition_authors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposition_source TEXT NOT NULL,
  proposition_external_id TEXT NOT NULL,
  parlamentar_external_id TEXT,
  author_name TEXT,
  author_type TEXT,
  signature_order INTEGER,
  proponent INTEGER DEFAULT 0,
  updated_at TEXT NOT NULL,
  UNIQUE(proposition_source, proposition_external_id, author_name, signature_order)
);

CREATE TABLE IF NOT EXISTS proposition_themes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposition_source TEXT NOT NULL,
  proposition_external_id TEXT NOT NULL,
  theme_code TEXT,
  theme_name TEXT,
  relevance REAL DEFAULT 0,
  updated_at TEXT NOT NULL,
  UNIQUE(proposition_source, proposition_external_id, theme_code)
);

CREATE TABLE IF NOT EXISTS proposition_trackings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposition_source TEXT NOT NULL,
  proposition_external_id TEXT NOT NULL,
  sequencia INTEGER,
  data_hora TEXT,
  orgao_sigla TEXT,
  orgao_id TEXT,
  descricao_tramitacao TEXT,
  codigo_tipo_tramitacao TEXT,
  descricao_situacao TEXT,
  codigo_situacao INTEGER,
  despacho TEXT,
  url TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE(proposition_source, proposition_external_id, sequencia)
);

CREATE INDEX IF NOT EXISTS idx_parlamentarians_house ON parlamentarians(casa);
CREATE INDEX IF NOT EXISTS idx_propositions_house ON propositions(casa);
CREATE INDEX IF NOT EXISTS idx_propositions_year ON propositions(ano);
CREATE INDEX IF NOT EXISTS idx_expenses_parliamentarian ON expenses(parlamentar_external_id);
CREATE INDEX IF NOT EXISTS idx_expenses_year_month ON expenses(ano, mes);
CREATE INDEX IF NOT EXISTS idx_organ_memberships_parlamentarian ON organ_memberships(parlamentar_external_id);
CREATE INDEX IF NOT EXISTS idx_proposition_authors_proposition ON proposition_authors(proposition_external_id);
CREATE INDEX IF NOT EXISTS idx_proposition_trackings_proposition ON proposition_trackings(proposition_external_id);
"""
