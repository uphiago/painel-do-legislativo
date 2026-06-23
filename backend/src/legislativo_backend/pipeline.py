from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

from legislativo_backend.collectors import camara, senado
from legislativo_backend.db import LocalDatabase
from legislativo_backend.normalizers import (
    ProposicaoResumo,
    normalize_camara_ceap_archive_row,
    normalize_camara_deputado,
    normalize_camara_despesa,
    normalize_camara_proposicao,
    normalize_senado_processo,
    normalize_senado_senador,
)
from legislativo_backend.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

MAX_PARALLEL = 4  # Workers paralelos (respeita rate-limiter que e thread-safe)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def collect_reference_data(database: LocalDatabase, supabase: SupabaseClient | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}

    tipos = camara.list_referencia_tipos_proposicao()
    tipo_rows = [
        {"codigo": str(t["cod"]), "sigla": t.get("sigla"), "nome": t.get("nome"), "descricao": t.get("descricao")}
        for t in tipos.get("dados", [])
    ]
    database.upsert_proposition_types(tipo_rows)
    if supabase:
        supabase.upsert_proposition_types(tipo_rows)
    counts["proposition_types"] = len(tipo_rows)

    legislaturas = camara.list_legislatures(limit=100)
    legis_rows = [
        {
            "source": "camara", "external_id": str(leg["id"]), "numero": leg.get("id"),
            "data_inicio": leg.get("dataInicio"), "data_fim": leg.get("dataFim"),
        }
        for leg in legislaturas.get("dados", [])
    ]
    database.upsert_legislatures(legis_rows)
    if supabase:
        supabase.upsert_legislatures(legis_rows)
    counts["legislatures"] = len(legis_rows)

    partidos = camara.list_partidos(limit=200)
    party_rows = [
        {
            "source": "camara", "external_id": str(p["id"]), "sigla": p["sigla"],
            "nome": p.get("nome"), "logo_url": None,
        }
        for p in partidos.get("dados", [])
    ]
    database.upsert_parties(party_rows)
    if supabase:
        supabase.upsert_parties(party_rows)
    counts["parties"] = len(party_rows)

    orgaos = camara.list_all_orgaos(page_size=100)
    organ_rows = [
        {
            "source": "camara", "external_id": str(o["id"]), "sigla": o.get("sigla"),
            "nome": o.get("nome"), "tipo": o.get("tipoOrgao"), "casa": "camara",
            "data_inicio": o.get("dataInicio"), "data_fim": o.get("dataFim"),
        }
        for o in orgaos
    ]
    database.upsert_organs(organ_rows)
    if supabase:
        supabase.upsert_organs(organ_rows)
    counts["organs"] = len(organ_rows)

    processo_siglas = senado.list_processo_siglas()
    if isinstance(processo_siglas, list):
        counts["processo_siglas"] = len(processo_siglas)

    return counts


def collect_all_parliamentarians(database: LocalDatabase, supabase: SupabaseClient | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}

    deputados = camara.list_all_deputados(page_size=100)
    dep_rows = [normalize_camara_deputado(d) for d in deputados]
    database.upsert_parlamentarians(dep_rows)
    if supabase:
        supabase.upsert_parlamentarians([r.model_dump() for r in dep_rows])
    counts["camara_parlamentarians"] = len(dep_rows)

    senadores_raw = senado.list_senadores_atual()
    raw = senadores_raw.get("ListaParlamentarEmExercicio", {})
    parlamentares = raw.get("Parlamentares", {})
    items = parlamentares.get("Parlamentar", [])
    senadores_list = items if isinstance(items, list) else ([items] if isinstance(items, dict) else [])
    sen_rows = [normalize_senado_senador(s) for s in senadores_list]
    database.upsert_parlamentarians(sen_rows)
    if supabase:
        supabase.upsert_parlamentarians([r.model_dump() for r in sen_rows])
    counts["senado_parlamentarians"] = len(sen_rows)

    return counts


def enrich_deputado_completo(
    database: LocalDatabase,
    deputado_id: int,
    supabase: SupabaseClient | None = None,
    anos_despesas: list[int] | None = None,
) -> dict[str, int]:
    """Coleta TUDO disponivel sobre um deputado."""
    c: dict[str, int] = {"propositions": 0, "expenses": 0, "events": 0, "errors": 0}
    anos = anos_despesas or [2025, 2024, 2023]

    try:
        detail = camara.get_deputado_detail(deputado_id)
        dados = detail.get("dados", {})

        orgaos_raw = camara.list_deputado_orgaos(deputado_id)

        frentes_raw = camara.list_deputado_frentes(deputado_id)

        eventos_raw = camara.list_deputado_eventos(deputado_id, limit=100)
        eventos_list = eventos_raw.get("dados", [])
        c["events"] = len(eventos_list)

        props_raw = camara.list_all_deputado_proposicoes(deputado_id, page_size=100)
        prop_rows = [normalize_camara_proposicao(pr) for pr in props_raw]
        if prop_rows:
            database.upsert_propositions(prop_rows)
            if supabase:
                try:
                    supabase.upsert_propositions([r.model_dump() for r in prop_rows])
                except Exception:
                    logger.warning("Supabase: falha ao upsert proposicoes deputado %s", deputado_id, exc_info=True)
            c["propositions"] = len(prop_rows)

        for ano in anos:
            try:
                despesas = camara.list_all_deputado_despesas(deputado_id, ano, page_size=100)
                if despesas:
                    exp_rows = [normalize_camara_despesa(dr, deputado_id) for dr in despesas]
                    database.upsert_expenses(exp_rows)
                    if supabase:
                        try:
                            supabase.upsert_expenses([r.model_dump() for r in exp_rows])
                        except Exception:
                            logger.warning("Supabase: falha ao upsert despesas deputado %s ano %s", deputado_id, ano, exc_info=True)
                    c["expenses"] += len(exp_rows)
            except Exception:
                logger.warning(
                    "Falha ao coletar despesas do deputado %s no ano %s",
                    deputado_id,
                    ano,
                    exc_info=True,
                )

        payload = {
            "detail": detail,
            "orgaos": orgaos_raw,
            "frentes": frentes_raw,
            "eventos": eventos_raw,
            "total_proposicoes": len(props_raw),
        }
        database.upsert_raw_payload(
            source="camara", kind="deputado-full",
            external_id=str(deputado_id), payload=payload,
        )
        if supabase:
            supabase.upsert_raw_payload("camara", "deputado-full", str(deputado_id), payload)

        orgaos_list = orgaos_raw.get("dados", [])
        if orgaos_list:
            organ_rows = [
                {"source": "camara", "external_id": str(o.get("idOrgao")),
                 "sigla": o.get("siglaOrgao"), "nome": o.get("nomeOrgao"),
                 "tipo": None, "casa": "camara"} for o in orgaos_list
            ]
            database.upsert_organs(organ_rows)
            if supabase:
                try:
                    supabase.upsert_organs(organ_rows)
                except Exception:
                    logger.warning("Supabase: falha ao upsert orgaos deputado %s", deputado_id, exc_info=True)
            membership_rows = [
                {"parliamentarian_external_id": str(deputado_id), "source": "camara",
                 "organ_external_id": str(o.get("idOrgao")), "role": o.get("titulo"),
                 "data_inicio": o.get("dataInicio"), "data_fim": o.get("dataFim")}
                for o in orgaos_list
            ]
            database.upsert_organ_memberships(membership_rows)
            if supabase:
                try:
                    supabase.upsert_organ_memberships(membership_rows)
                except Exception:
                    logger.warning("Supabase: falha ao upsert organ_memberships deputado %s", deputado_id, exc_info=True)

        frentes_list = frentes_raw.get("dados", [])
        if frentes_list:
            front_rows = [
                {"external_id": str(f["id"]), "titulo": f.get("titulo"),
                 "legislature_id": f.get("idLegislatura")} for f in frentes_list
            ]
            database.upsert_frentes(front_rows)
            if supabase:
                try:
                    supabase.upsert_frentes(front_rows)
                except Exception:
                    logger.warning("Supabase: falha ao upsert frentes deputado %s", deputado_id, exc_info=True)
            fm_rows = [
                {"front_external_id": str(f["id"]),
                 "parliamentarian_external_id": str(deputado_id),
                 "legislature_id": f.get("idLegislatura")} for f in frentes_list
            ]
            database.upsert_front_memberships(fm_rows)
            if supabase:
                try:
                    supabase.upsert_front_memberships(fm_rows)
                except Exception:
                    logger.warning("Supabase: falha ao upsert front_memberships deputado %s", deputado_id, exc_info=True)

        mandate_data = dados.get("ultimoStatus", {})
        mandate_rows = [{
            "parliamentarian_external_id": str(deputado_id), "source": "camara",
            "legislature_id": str(mandate_data.get("idLegislatura")),
            "party_sigla": mandate_data.get("siglaPartido"),
            "uf": mandate_data.get("siglaUf"),
            "status": mandate_data.get("situacao"),
            "condition": mandate_data.get("condicaoEleitoral"),
            "data_inicio": mandate_data.get("data"),
        }]
        database.upsert_mandates(mandate_rows)
        if supabase:
            try:
                supabase.upsert_mandates(mandate_rows)
            except Exception:
                logger.warning("Supabase: falha ao upsert mandates deputado %s", deputado_id, exc_info=True)

    except Exception as exc:
        c["errors"] += 1
        database.upsert_raw_payload(
            source="camara", kind="deputado-error",
            external_id=str(deputado_id),
            payload={"id": deputado_id, "error": str(exc)[:500]},
        )

    return c


def enrich_senador_completo(
    database: LocalDatabase,
    codigo: int,
    supabase: SupabaseClient | None = None,
) -> dict[str, int]:
    """Coleta TUDO disponivel sobre um senador."""
    c: dict[str, int] = {"propositions": 0, "mandatos": 0, "discursos": 0, "errors": 0}

    try:
        comissoes_raw = senado.list_senador_comissoes(codigo)
        mandatos_raw = senado.list_senador_mandatos(codigo)
        filiacoes_raw = senado.list_senador_filiacoes(codigo)
        discursos_raw = senado.list_senador_discursos(codigo)
        relatorias_raw = senado.list_senador_relatorias(codigo)
        cargos_raw = senado.list_senador_cargos(codigo)
        liderancas_raw = senado.list_senador_liderancas(codigo)

        licencas_raw = None
        profissao_raw = None
        academico_raw = None
        try:
            licencas_raw = senado.list_senador_licencas(codigo)
        except Exception:
            logger.debug("Licencas indisponiveis para senador %s", codigo, exc_info=True)
        try:
            profissao_raw = senado.list_senador_profissao(codigo)
        except Exception:
            logger.debug("Profissao indisponivel para senador %s", codigo, exc_info=True)
        try:
            academico_raw = senado.list_senador_historico_academico(codigo)
        except Exception:
            logger.debug("Historico academico indisponivel para senador %s", codigo, exc_info=True)

        processos = senado.list_processos_by_parlamentar(codigo)
        if isinstance(processos, list) and processos:
            proc_rows = [normalize_senado_processo(pr) for pr in processos]
            database.upsert_propositions(proc_rows)
            if supabase:
                try:
                    supabase.upsert_propositions([r.model_dump() for r in proc_rows])
                except Exception:
                    logger.warning("Supabase: falha ao upsert processos senador %s", codigo, exc_info=True)
            c["propositions"] = len(proc_rows)

        mandatos_data = mandatos_raw.get("MandatoParlamentar", {})
        if mandatos_data:
            c["mandatos"] = 1
        filiacoes_data = filiacoes_raw.get("FiliacaoParlamentar", {})
        if filiacoes_data:
            c["filiacoes"] = 1

        discursos_lista = discursos_raw.get("Discursos", {}).get("Discurso", [])
        if isinstance(discursos_lista, list):
            c["discursos"] = len(discursos_lista)
        elif isinstance(discursos_lista, dict):
            c["discursos"] = 1

        payload = {
            "comissoes": comissoes_raw,
            "mandatos": mandatos_raw,
            "filiacoes": filiacoes_raw,
            "discursos": discursos_raw,
            "relatorias": relatorias_raw,
            "cargos": cargos_raw,
            "liderancas": liderancas_raw,
            "licencas": licencas_raw,
            "profissao": profissao_raw,
            "historico_academico": academico_raw,
            "total_processos": len(processos) if isinstance(processos, list) else 0,
        }
        database.upsert_raw_payload(
            source="senado", kind="senador-full",
            external_id=str(codigo), payload=payload,
        )
        if supabase:
            supabase.upsert_raw_payload("senado", "senador-full", str(codigo), payload)

    except Exception as exc:
        c["errors"] += 1
        database.upsert_raw_payload(
            source="senado", kind="senador-error",
            external_id=str(codigo),
            payload={"codigo": codigo, "error": str(exc)[:500]},
        )

    return c


def enrich_proposicao_completa(
    database: LocalDatabase,
    prop_id: int,
    source: str = "camara",
    supabase: SupabaseClient | None = None,
) -> dict[str, int]:
    """Coleta TUDO disponivel sobre uma proposicao."""
    c: dict[str, int] = {"authors": 0, "themes": 0, "trackings": 0, "votings": 0, "errors": 0}

    try:
        autores_raw = camara.list_proposicao_autores(prop_id)
        autores = autores_raw.get("dados", [])
        author_rows = [
            {
                "proposition_source": "camara", "proposition_external_id": str(prop_id),
                "parliamentarian_external_id": None,
                "author_name": a.get("nome"), "author_type": a.get("tipo"),
                "signature_order": a.get("ordemAssinatura"),
                "proponent": 1 if a.get("proponente") == 1 else 0,
            }
            for a in autores
        ]
        if author_rows:
            database.upsert_proposition_authors(author_rows)
            if supabase:
                supabase.upsert_proposition_authors(author_rows)
            c["authors"] += len(author_rows)

        temas_raw = camara.list_proposicao_temas(prop_id)
        temas = temas_raw.get("dados", [])
        theme_rows = [
            {
                "proposition_source": "camara", "proposition_external_id": str(prop_id),
                "theme_code": str(t.get("codTema")), "theme_name": t.get("tema"),
                "relevance": t.get("relevancia", 0),
            }
            for t in temas
        ]
        if theme_rows:
            database.upsert_proposition_themes(theme_rows)
            if supabase:
                supabase.upsert_proposition_themes(theme_rows)
            c["themes"] += len(theme_rows)

        tramitacoes_raw = camara.list_proposicao_tramitacoes(prop_id)
        tramitacoes = tramitacoes_raw.get("dados", [])
        tracking_rows = [
            {
                "proposition_source": "camara", "proposition_external_id": str(prop_id),
                "sequencia": tr.get("sequencia"), "data_hora": tr.get("dataHora"),
                "orgao_sigla": tr.get("siglaOrgao"), "orgao_id": None,
                "descricao_tramitacao": tr.get("descricaoTramitacao"),
                "codigo_tipo_tramitacao": tr.get("codTipoTramitacao"),
                "descricao_situacao": tr.get("descricaoSituacao"),
                "codigo_situacao": tr.get("codSituacao"),
                "despacho": tr.get("despacho"), "url": tr.get("url"),
            }
            for tr in tramitacoes
        ]
        if tracking_rows:
            database.upsert_proposition_trackings(tracking_rows)
            if supabase:
                supabase.upsert_proposition_trackings(tracking_rows)
            c["trackings"] += len(tracking_rows)

        votacoes_raw = camara.list_votacoes_by_proposicao(prop_id, limit=50)
        votacoes = votacoes_raw.get("dados", [])
        c["votings"] = len(votacoes)

        detail = camara.get_proposicao_detail(prop_id)

        database.upsert_raw_payload(
            source="camara", kind="proposicao-full",
            external_id=str(prop_id),
            payload={
                "detail": detail, "autores": autores_raw, "temas": temas_raw,
                "tramitacoes": tramitacoes_raw, "votacoes": votacoes_raw,
            },
        )

    except Exception as exc:
        c["errors"] += 1
        database.upsert_raw_payload(
            source="camara", kind="proposicao-error",
            external_id=str(prop_id),
            payload={"id": prop_id, "error": str(exc)[:500]},
        )

    return c


def enrich_proposicoes_senado(
    database: LocalDatabase,
    processo_id: int,
    supabase: SupabaseClient | None = None,
) -> dict[str, int]:
    c: dict[str, int] = {"detail": 0, "documentos": 0, "errors": 0}
    try:
        detail = senado.get_processo_detail(processo_id)

        documentos_raw = None
        emendas_raw = None
        try:
            documentos_raw = senado.list_processo_documentos(processo_id)
            if isinstance(documentos_raw, list):
                c["documentos"] = len(documentos_raw)
        except Exception:
            logger.debug("Documentos indisponiveis para processo %s", processo_id, exc_info=True)
        try:
            emendas_raw = senado.list_processo_emendas(processo_id)
        except Exception:
            logger.debug("Emendas indisponiveis para processo %s", processo_id, exc_info=True)

        database.upsert_raw_payload(
            source="senado", kind="processo-full",
            external_id=str(processo_id),
            payload={"detail": detail, "documentos": documentos_raw, "emendas": emendas_raw},
        )
        c["detail"] = 1
    except Exception as exc:
        c["errors"] += 1
        database.upsert_raw_payload(
            source="senado", kind="processo-error",
            external_id=str(processo_id),
            payload={"id": processo_id, "error": str(exc)[:500]},
        )
    return c


def _prop_id_from_bulk(item: dict[str, Any]) -> str | None:
    if "id" in item:
        return str(item["id"])
    uri = item.get("uri") or item.get("uriProposicao", "")
    parts = uri.rstrip("/").rsplit("/", 1)
    return parts[-1] if parts[-1].isdigit() else None


def _idprop_from_bulk(item: dict[str, Any]) -> str | None:
    return str(item["idProposicao"]) if "idProposicao" in item else _prop_id_from_bulk(item)


def collect_bulk_complete_year(
    database: LocalDatabase,
    ano: int,
    supabase: SupabaseClient | None = None,
) -> dict[str, int]:
    """Baixa e importa proposicoes + temas + autores de um ano inteiro via arquivos bulk."""
    c: dict[str, int] = {"propositions": 0, "themes": 0, "authors": 0, "errors": 0}

    try:
        dados = camara.download_proposicoes_arquivo(ano)
        if isinstance(dados, list) and dados:
            normalized: list[ProposicaoResumo] = []
            for item in dados:
                if not isinstance(item, dict):
                    continue
                prop_id = _prop_id_from_bulk(item)
                if not prop_id:
                    continue
                normalized.append(normalize_camara_proposicao({**item, "id": int(prop_id)}))
            if normalized:
                c["propositions"] = database.insert_propositions_bulk(normalized)
            if supabase and normalized:
                BATCH = 5000
                for i in range(0, len(normalized), BATCH):
                    batch = [r.model_dump() for r in normalized[i:i + BATCH]]
                    try:
                        supabase.upsert_propositions(batch)
                    except Exception:
                        logger.warning(
                            "Falha ao sincronizar batch de proposicoes com Supabase (offset %d)",
                            i,
                            exc_info=True,
                        )
    except Exception as exc:
        c["errors"] += 1
        database.upsert_raw_payload(
            source="camara", kind="bulk-error",
            external_id=f"proposicoes-{ano}", payload={"ano": ano, "error": str(exc)[:500]},
        )

    try:
        temas_raw = camara.download_proposicoes_temas_arquivo(ano)
        if isinstance(temas_raw, list) and temas_raw:
            theme_batch: list[dict[str, Any]] = []
            for t in temas_raw:
                if not isinstance(t, dict):
                    continue
                prop_id = _prop_id_from_bulk(t)
                if not prop_id:
                    continue
                theme_batch.append({
                    "proposition_source": "camara",
                    "proposition_external_id": prop_id,
                    "theme_code": str(t.get("codTema", "")),
                    "theme_name": str(t.get("tema", "")),
                    "relevance": t.get("relevancia", 0),
                })
                if len(theme_batch) >= 5000:
                    c["themes"] += database.upsert_proposition_themes(theme_batch)
                    if supabase:
                        supabase.upsert_proposition_themes(theme_batch)
                    theme_batch.clear()
            if theme_batch:
                c["themes"] += database.upsert_proposition_themes(theme_batch)
                if supabase:
                    supabase.upsert_proposition_themes(theme_batch)
    except Exception as exc:
        c["errors"] += 1
        database.upsert_raw_payload(
            source="camara", kind="bulk-error",
            external_id=f"temas-{ano}", payload={"ano": ano, "error": str(exc)[:500]},
        )

    try:
        autores_raw = camara.download_proposicoes_autores_arquivo(ano)
        if isinstance(autores_raw, list) and autores_raw:
            author_batch: list[dict[str, Any]] = []
            for a in autores_raw:
                if not isinstance(a, dict):
                    continue
                prop_id = _idprop_from_bulk(a)
                if not prop_id:
                    continue
                author_uri = str(a.get("uriAutor", ""))
                parl_id = None
                if "/deputados/" in author_uri:
                    parl_id = author_uri.rstrip("/").rsplit("/", 1)[-1]
                author_batch.append({
                    "proposition_source": "camara",
                    "proposition_external_id": prop_id,
                    "parliamentarian_external_id": parl_id,
                    "author_name": a.get("nomeAutor"),
                    "author_type": a.get("tipoAutor"),
                    "signature_order": int(a["ordemAssinatura"]) if a.get("ordemAssinatura") and str(a["ordemAssinatura"]).isdigit() else None,
                    "proponent": 1 if str(a.get("proponente", "0")) == "1" else 0,
                })
                if len(author_batch) >= 5000:
                    c["authors"] += database.upsert_proposition_authors(author_batch)
                    if supabase:
                        supabase.upsert_proposition_authors(author_batch)
                    author_batch.clear()
            if author_batch:
                c["authors"] += database.upsert_proposition_authors(author_batch)
                if supabase:
                    supabase.upsert_proposition_authors(author_batch)
    except Exception as exc:
        c["errors"] += 1
        database.upsert_raw_payload(
            source="camara", kind="bulk-error",
            external_id=f"autores-{ano}", payload={"ano": ano, "error": str(exc)[:500]},
        )

    database.record_sync_run(
        job="bulk:complete-year",
        source="camara",
        status="success" if c["errors"] == 0 else "partial",
        records_count=c["propositions"] + c["themes"] + c["authors"],
        metadata={"ano": ano, **c},
    )
    if supabase:
        supabase.record_sync_run(
            job="bulk:complete-year",
            source="camara",
            status="success" if c["errors"] == 0 else "partial",
            records_count=c["propositions"] + c["themes"] + c["authors"],
            metadata={"ano": ano, **c},
        )
        supabase.refresh_materialized_views()
    return c


def enrich_deputados(
    database: LocalDatabase,
    supabase: SupabaseClient | None = None,
    limit: int = 10,
    offset: int = 0,
    anos_despesas: list[int] | None = None,
    parallel: bool = False,
) -> dict[str, Any]:
    """Wrapper que chama enrich_deputado_completo para lote de deputados."""
    totals: dict[str, int] = {}
    parlamentares = database.list_parliamentarians(source="camara", limit=limit, offset=offset)
    enriched = database.get_enriched_parliamentarian_ids("camara")
    pending = [(int(p["external_id"]), p.get("name", p.get("nome", "?"))) for p in parlamentares if p["external_id"] not in enriched]
    skipped = len(parlamentares) - len(pending)
    totals["skipped"] = skipped

    if not pending:
        totals["profiles"] = 0
        return totals

    if parallel and len(pending) > 1:
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
            futures = {
                pool.submit(enrich_deputado_completo, database, did, supabase, anos_despesas): did
                for did, _ in pending
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    for k, v in result.items():
                        totals[k] = totals.get(k, 0) + v
                except Exception:
                    totals["errors"] = totals.get("errors", 0) + 1
    else:
        for did, nome in pending:
            result = enrich_deputado_completo(database, did, supabase, anos_despesas)
            for k, v in result.items():
                totals[k] = totals.get(k, 0) + v

    totals["profiles"] = len(pending) - totals.get("errors", 0)
    return totals


def enrich_senadores(
    database: LocalDatabase,
    supabase: SupabaseClient | None = None,
    limit: int = 10,
    offset: int = 0,
    parallel: bool = False,
) -> dict[str, Any]:
    """Wrapper que chama enrich_senador_completo para lote de senadores."""
    totals: dict[str, int] = {}
    senadores = database.list_parliamentarians(source="senado", limit=limit, offset=offset)
    enriched = database.get_enriched_parliamentarian_ids("senado")
    pending = [(int(s["external_id"]), s.get("name", s.get("nome", "?"))) for s in senadores if s["external_id"] not in enriched]
    skipped = len(senadores) - len(pending)
    totals["skipped"] = skipped

    if not pending:
        totals["profiles"] = 0
        return totals

    if parallel and len(pending) > 1:
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
            futures = {
                pool.submit(enrich_senador_completo, database, cod, supabase): cod
                for cod, _ in pending
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    for k, v in result.items():
                        totals[k] = totals.get(k, 0) + v
                except Exception:
                    totals["errors"] = totals.get("errors", 0) + 1
    else:
        for cod, nome in pending:
            result = enrich_senador_completo(database, cod, supabase)
            for k, v in result.items():
                totals[k] = totals.get(k, 0) + v

    totals["profiles"] = len(pending) - totals.get("errors", 0)
    return totals


def enrich_proposicoes_camara(
    database: LocalDatabase,
    supabase: SupabaseClient | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Wrapper que chama enrich_proposicao_completa para lote de proposicoes."""
    totals: dict[str, int] = {}
    proposicoes = database.list_propositions(source="camara", limit=limit, offset=offset)
    for prop in proposicoes:
        pid = int(prop["external_id"])
        result = enrich_proposicao_completa(database, pid, source="camara", supabase=supabase)
        for k, v in result.items():
            totals[k] = totals.get(k, 0) + v
    totals["details"] = len(proposicoes) - totals.get("errors", 0)
    return totals


def full_pipeline(
    database: LocalDatabase,
    supabase: SupabaseClient | None = None,
    batch_size: int = 10,
    anos_despesas: list[int] | None = None,
    anos_proposicoes: list[int] | None = None,
) -> dict[str, Any]:
    start = time.time()
    results: dict[str, Any] = {}
    anos = anos_despesas or [2025, 2024, 2023]

    results["reference"] = collect_reference_data(database, supabase)
    results["parlamentares"] = collect_all_parliamentarians(database, supabase)

    camara_total = results["parlamentares"].get("camara_parlamentarians", 0)
    senado_total = results["parlamentares"].get("senado_parliamentarians", 0)

    camara_totals: dict[str, int] = {}
    camara_batches = (camara_total + batch_size - 1) // batch_size
    for b in range(camara_batches):
        offset = b * batch_size
        br = enrich_deputados(database, supabase, limit=batch_size, offset=offset, anos_despesas=anos)
        for k, v in br.items():
            camara_totals[k] = camara_totals.get(k, 0) + v
    results["camara_enrich"] = camara_totals

    senado_totals: dict[str, int] = {}
    senado_batches = (senado_total + batch_size - 1) // batch_size
    for b in range(senado_batches):
        offset = b * batch_size
        br = enrich_senadores(database, supabase, limit=batch_size, offset=offset)
        for k, v in br.items():
            senado_totals[k] = senado_totals.get(k, 0) + v
    results["senado_enrich"] = senado_totals

    if anos_proposicoes:
        bulk_totals: dict[str, int] = {}
        for ano in anos_proposicoes:
            br = collect_bulk_complete_year(database, ano, supabase)
            for k, v in br.items():
                bulk_totals[k] = bulk_totals.get(k, 0) + v
        results["bulk_years"] = bulk_totals

    results["proposition_enrich"] = enrich_proposicoes_incremental(
        database, supabase, batch_size=batch_size, max_batches=20, min_ano=2024,
    )

    elapsed = time.time() - start
    results["elapsed_seconds"] = round(elapsed, 1)
    results["summary"] = database.summary()

    database.record_sync_run(
        job="pipeline:full",
        source="all",
        status="success",
        records_count=camara_total + senado_total,
        metadata=results,
    )
    if supabase:
        supabase.record_sync_run(
            job="pipeline:full",
            source="all",
            status="success",
            records_count=camara_total + senado_total,
            metadata=results,
        )
        supabase.refresh_materialized_views()

    return results


def enrich_proposicoes_incremental(
    database: LocalDatabase,
    supabase: SupabaseClient | None = None,
    batch_size: int = 25,
    max_batches: int | None = None,
    min_ano: int | None = None,
) -> dict[str, int]:
    """Enriquece proposicoes nao processadas, priorizando anos recentes. Permite resume."""
    totals: dict[str, int] = {"processed": 0, "authors": 0, "themes": 0, "trackings": 0, "errors": 0}
    total_pending = database.count_unenriched_propositions(source="camara", min_ano=min_ano)
    batches = (total_pending + batch_size - 1) // batch_size if total_pending > 0 else 0
    if max_batches is not None:
        batches = min(batches, max_batches)

    for b in range(batches):
        offset = b * batch_size
        props = database.list_unenriched_propositions(
            source="camara", limit=batch_size, offset=offset, min_ano=min_ano,
        )
        if not props:
            break
        for prop in props:
            pid = int(prop["external_id"])
            result = enrich_proposicao_completa(database, pid, supabase=supabase)
            for k, v in result.items():
                totals[k] = totals.get(k, 0) + v
        totals["processed"] += len(props)

    database.record_sync_run(
        job="pipeline:enrich-proposicoes-incremental",
        source="camara",
        status="success" if totals["errors"] == 0 else "partial",
        records_count=totals["processed"],
        metadata={**totals, "min_ano": min_ano, "pending_remaining": total_pending - totals["processed"]},
    )
    if supabase:
        supabase.record_sync_run(
            job="pipeline:enrich-proposicoes-incremental",
            source="camara",
            status="success" if totals["errors"] == 0 else "partial",
            records_count=totals["processed"],
            metadata={**totals, "min_ano": min_ano, "pending_remaining": total_pending - totals["processed"]},
        )
    return totals


def collect_bulk_ceap_year(
    database: LocalDatabase,
    ano: int,
    supabase: SupabaseClient | None = None,
) -> dict[str, int]:
    """Baixa o CSV ZIP da CEAP de um ano e importa todas as despesas."""
    c: dict[str, int] = {"expenses": 0, "errors": 0}
    try:
        rows = camara.download_ceap_csv_stream(ano)
        if rows:
            batch: list = []
            for row in rows:
                batch.append(normalize_camara_ceap_archive_row(row))
                if len(batch) >= 5000:
                    c["expenses"] += database.upsert_expenses(batch)
                    if supabase:
                        try:
                            supabase.upsert_expenses([r.model_dump() for r in batch])
                        except Exception:
                            logger.warning(
                                "Falha ao sincronizar batch de despesas CEAP com Supabase",
                                exc_info=True,
                            )
                    batch.clear()
            if batch:
                c["expenses"] += database.upsert_expenses(batch)
                if supabase:
                    try:
                        supabase.upsert_expenses([r.model_dump() for r in batch])
                    except Exception:
                        logger.warning(
                            "Falha ao sincronizar batch final de despesas CEAP com Supabase",
                            exc_info=True,
                        )
        database.record_sync_run(
            job="bulk:ceap-year",
            source="camara",
            status="success",
            records_count=c["expenses"],
            metadata={"ano": ano},
        )
        if supabase:
            supabase.record_sync_run(
                job="bulk:ceap-year",
                source="camara",
                status="success",
                records_count=c["expenses"],
                metadata={"ano": ano},
            )
    except Exception as exc:
        c["errors"] += 1
        database.upsert_raw_payload(
            source="camara", kind="bulk-error",
            external_id=f"ceap-{ano}", payload={"ano": ano, "error": str(exc)[:500]},
        )
    return c


def collect_discursos_senado(
    database: LocalDatabase,
    supabase: SupabaseClient | None = None,
    limit: int = 20,
    offset: int = 0,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> dict[str, int]:
    """Coleta discursos de senadores e persiste na tabela discursos."""
    c: dict[str, int] = {"discursos": 0, "erros": 0}

    senadores = database.list_parliamentarians(source="senado", limit=limit, offset=offset)

    for s in senadores:
        codigo = int(s["external_id"])
        try:
            discursos_raw = senado.list_senador_discursos(codigo, data_inicio, data_fim)
            parlamentar_data = discursos_raw.get("DiscursosParlamentar", {}).get("Parlamentar", {})
            discursos_lista = parlamentar_data.get("Pronunciamentos", {}).get("Pronunciamento", [])
            if discursos_lista is None:
                discursos_lista = []
            if isinstance(discursos_lista, dict):
                discursos_lista = [discursos_lista]

            rows: list[dict[str, Any]] = []
            for d in discursos_lista:
                if not isinstance(d, dict):
                    continue
                rows.append({
                    "senador_codigo": str(codigo),
                    "senador_nome": s.get("name", ""),
                    "data_discurso": d.get("DataDiscurso"),
                    "casa": "senado",
                    "tipo": d.get("TipoDiscurso"),
                    "resumo": (d.get("ResumoDiscurso") or "")[:500],
                    "texto_url": None,
                })

            local_count = database.upsert_discursos(rows)

            c["discursos"] += local_count

            if supabase and rows:
                try:
                    supabase.upsert_discursos(rows)
                except Exception:
                    logger.warning(
                        "Falha ao sincronizar discursos com Supabase", exc_info=True
                    )

        except Exception:
            c["erros"] += 1

    database.record_sync_run(
        job="pipeline:discursos-senado",
        source="senado",
        status="success" if c["erros"] == 0 else "partial",
        records_count=c["discursos"],
        metadata={**c, "limit": limit, "offset": offset},
    )
    if supabase:
        supabase.record_sync_run(
            job="pipeline:discursos-senado",
            source="senado",
            status="success" if c["erros"] == 0 else "partial",
            records_count=c["discursos"],
            metadata={**c, "limit": limit, "offset": offset},
        )
    return c


def collect_votacoes_ano(
    database: LocalDatabase,
    ano: int,
    source: str = "camara",
    supabase: SupabaseClient | None = None,
) -> dict[str, int]:
    """Coleta votações de um ano e seus votos da Câmara."""
    c: dict[str, int] = {"votacoes": 0, "votos": 0, "errors": 0}

    try:
        if source == "camara":
            votacoes_list = camara.list_all_votacoes_by_year(ano, page_size=100)
        else:
            logger.warning("Votacoes do Senado: use collect_votacoes_senado")
            return c

        for v in votacoes_list:
            try:
                votacao_id = v["id"]
                votacao_row = {
                    "source": source,
                    "external_id": str(votacao_id),
                    "proposicao_external_id": _extract_proposicao_id(v),
                    "sigla_orgao": v.get("siglaOrgao"),
                    "descricao": v.get("descricao"),
                    "data": v.get("data"),
                    "aprovada": v.get("aprovada"),
                }

                # Detalhe com votos
                detail = camara.get_votacao_detail(votacao_id)
                dados = detail.get("dados", {})
                votos_lista = dados.get("votos", [])

                voto_rows = []
                for vt in votos_lista:
                    dep = vt.get("deputado_", {})
                    if isinstance(dep, dict):
                        dep_id = str(dep.get("id", ""))
                    else:
                        dep_id = str(vt.get("idDeputado", ""))
                    if not dep_id:
                        continue
                    voto_rows.append({
                        "votacao_external_id": str(votacao_id),
                        "source": source,
                        "parlamentar_external_id": dep_id,
                        "parlamentar_nome": vt.get("nome") or (dep.get("nome") if isinstance(dep, dict) else None),
                        "voto": vt.get("tipoVoto") or vt.get("voto", ""),
                    })

                if supabase:
                    supabase.upsert_votacoes([votacao_row])
                    supabase.upsert_raw_payload(source, "votacao", str(votacao_id), detail)

                database.upsert_votacoes([votacao_row])
                database.upsert_raw_payload(
                    source=source, kind="votacao",
                    external_id=str(votacao_id), payload=detail,
                )

                if voto_rows:
                    database.upsert_votos(voto_rows)
                    if supabase:
                        try:
                            supabase.upsert_votos(voto_rows)
                        except Exception:
                            logger.warning("Supabase: falha ao upsert votos da votacao %s", votacao_id, exc_info=True)
                    c["votos"] += len(voto_rows)

                c["votacoes"] += 1

            except Exception:
                logger.warning("Falha ao coletar votacao %s", v.get("id"), exc_info=True)
                c["errors"] += 1

        database.record_sync_run(
            job="pipeline:votacoes-ano",
            source=source,
            status="success" if c["errors"] == 0 else "partial",
            records_count=c["votacoes"] + c["votos"],
            metadata={"ano": ano, **c},
        )
        if supabase:
            supabase.record_sync_run(
                job="pipeline:votacoes-ano",
                source=source,
                status="success" if c["errors"] == 0 else "partial",
                records_count=c["votacoes"] + c["votos"],
                metadata={"ano": ano, **c},
            )

    except Exception as exc:
        c["errors"] += 1
        database.upsert_raw_payload(
            source=source, kind="bulk-error",
            external_id=f"votacoes-{ano}", payload={"ano": ano, "error": str(exc)[:500]},
        )

    return c


def _extract_proposicao_id(votacao: dict) -> str | None:
    proposicoes = votacao.get("proposicoes", [])
    if isinstance(proposicoes, list) and proposicoes:
        p = proposicoes[0]
        if isinstance(p, dict):
            pid = p.get("id") or p.get("codigo")
            if pid:
                return str(pid)
            uri = p.get("uri", "")
            parts = uri.rstrip("/").rsplit("/", 1)
            return parts[-1] if parts[-1].isdigit() else None
    return None


def collect_emendas_portal(
    database: LocalDatabase,
    ano: int,
    supabase: SupabaseClient | None = None,
) -> dict[str, int]:
    """Coleta emendas parlamentares do Portal da Transparencia."""
    from legislativo_backend.collectors import portal_transparencia as pt

    c: dict[str, int] = {"emendas": 0, "errors": 0}
    try:
        rows = pt.list_all_emendas(ano=ano)
    except Exception as exc:
        logger.warning("Portal da Transparencia indisponivel: %s", exc)
        c["errors"] += 1
        database.record_sync_run(
            job="pipeline:emendas-portal", source="portal_transparencia",
            status="error", records_count=0, metadata={"ano": ano, "error": str(exc)[:200]},
        )
        return c

    emenda_rows = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        emenda_rows.append({
            "codigo_emenda": str(item.get("codigoEmenda") or item.get("codigo", "")),
            "ano": item.get("ano") or ano,
            "numero": str(item.get("numero", "")),
            "tipo": item.get("tipoEmenda") or item.get("tipo", ""),
            "autor": item.get("autor") or item.get("nomeAutor", ""),
            "valor": float(item.get("valorEmenda") or item.get("valor", 0)),
            "objeto": item.get("objeto") or item.get("funcao", ""),
            "uf": item.get("uf") or item.get("ufEmenda", ""),
            "orgao_concedente": item.get("orgaoConcedente") or item.get("orgao", ""),
            "data_publicacao": item.get("dataPublicacao", ""),
        })

    if emenda_rows:
        now = _now()
        with database.connect() as conn:
            conn.executemany(
                """INSERT OR IGNORE INTO emendas
                   (codigo_emenda, ano, numero, tipo, autor, valor, objeto, uf, orgao_concedente, data_publicacao, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [(r["codigo_emenda"], r["ano"], r["numero"], r["tipo"], r["autor"],
                  r["valor"], r["objeto"], r["uf"], r["orgao_concedente"], r["data_publicacao"], now)
                 for r in emenda_rows],
            )
        if supabase:
            try:
                supabase.upsert_emendas(emenda_rows)
            except Exception:
                logger.warning("Supabase: falha ao upsert emendas", exc_info=True)
        c["emendas"] = len(emenda_rows)

    database.record_sync_run(
        job="pipeline:emendas-portal", source="portal_transparencia",
        status="success" if c["errors"] == 0 else "partial",
        records_count=c["emendas"], metadata={"ano": ano},
    )
    if supabase:
        supabase.record_sync_run(
            job="pipeline:emendas-portal", source="portal_transparencia",
            status="success" if c["errors"] == 0 else "partial",
            records_count=c["emendas"], metadata={"ano": ano},
        )
    return c
