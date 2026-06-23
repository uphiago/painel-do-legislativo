from __future__ import annotations

import csv
import zipfile
from pathlib import Path
from typing import Annotated, Any

import typer

from legislativo_backend.collectors.camara import (
    get_deputado_detail,
    get_proposicao_detail,
    list_all_deputados,
    list_deputado_despesas,
    list_deputado_frentes,
    list_deputado_orgaos,
    list_deputado_proposicoes,
    list_deputados,
    list_proposicoes_by_year,
    list_proposicao_autores,
    list_proposicao_temas,
    list_proposicao_tramitacoes,
    list_referencia_tipos_proposicao,
    list_partidos,
    list_legislatures,
)
from legislativo_backend.collectors.senado import (
    get_processo_detail,
    list_processos_by_parlamentar,
    list_processos_by_termo,
    list_senador_autorias,
    list_senador_ceaps,
    list_senador_comissoes,
    list_senadores_atual,
)
from legislativo_backend.db import LocalDatabase
from legislativo_backend.normalizers import (
    ensure_list,
    normalize_camara_ceap_archive_row,
    normalize_camara_deputado,
    normalize_camara_despesa,
    normalize_camara_proposicao,
    normalize_senado_autoria,
    normalize_senado_ceaps,
    normalize_senado_processo,
    normalize_senado_senador,
)
from legislativo_backend.storage import write_snapshot

app = typer.Typer(help="Coletores do Painel do Legislativo.")
discover_app = typer.Typer(help="Coleta amostras oficiais e salva snapshots locais.")
db_app = typer.Typer(help="Gerencia o banco SQLite local de desenvolvimento.")
collect_app = typer.Typer(help="Coleta dados oficiais e grava no SQLite local.")
import_app = typer.Typer(help="Importa arquivos oficiais baixados para o SQLite local.")
pipeline_app = typer.Typer(help="Pipeline completo de coleta e sincronia.")
app.add_typer(discover_app, name="discover")
app.add_typer(db_app, name="db")
app.add_typer(collect_app, name="collect")
app.add_typer(import_app, name="import")
app.add_typer(pipeline_app, name="pipeline")

DbPathOption = Annotated[Path | None, typer.Option("--db-path", "--path")]


def _print_summary(
    title: str,
    raw_count: int,
    normalized: list[Any],
    snapshot_name: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    path = write_snapshot(
        snapshot_name,
        {"raw_count": raw_count, "metadata": metadata or {}, "normalized": normalized},
    )
    typer.echo(f"{title}")
    typer.echo(f"- itens brutos: {raw_count}")
    typer.echo(f"- itens normalizados: {len(normalized)}")
    typer.echo(f"- snapshot: {path}")
    if normalized:
        typer.echo("- primeiro item:")
        typer.echo(normalized[0])


def _db(path: Path | None = None) -> LocalDatabase:
    database = LocalDatabase(path)
    database.init()
    return database


def _safe_senadores_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai a lista de parlamentares do payload do Senado, lidando com dict/list."""
    exercicio = payload.get("ListaParlamentarEmExercicio", {})
    parlamentares = exercicio.get("Parlamentares", {})
    return ensure_list(parlamentares.get("Parlamentar"))


def _echo_db_summary(database: LocalDatabase) -> None:
    typer.echo(f"banco: {database.path}")
    for table, count in database.summary().items():
        typer.echo(f"{table}: {count}")


@db_app.command("init")
def init_db(path: DbPathOption = None) -> None:
    database = _db(path)
    typer.echo(f"banco inicializado: {database.path}")


@db_app.command("summary")
def summary_db(path: DbPathOption = None) -> None:
    _echo_db_summary(_db(path))


@db_app.command("coverage")
def coverage_db(path: DbPathOption = None) -> None:
    coverage = _db(path).coverage()
    camara_total = coverage["camara_parlamentarians"]
    senado_total = coverage["senado_parliamentarians"]
    camara_profiles = coverage["camara_profiles"]
    senado_profiles = coverage["senado_profiles"]
    typer.echo(f"camara parlamentares: {camara_profiles}/{camara_total} enriquecidos")
    typer.echo(f"senado parlamentares: {senado_profiles}/{senado_total} enriquecidos")
    typer.echo(f"proximo camara offset: {camara_profiles}")
    typer.echo(f"proximo senado offset: {senado_profiles}")


@import_app.command("camara-ceap-zip")
def import_camara_ceap_zip(
    zip_path: Annotated[Path, typer.Option("--zip-path", exists=True, file_okay=True)],
    db_path: DbPathOption = None,
    batch_size: Annotated[int, typer.Option("--batch-size", min=1, max=10000)] = 5000,
) -> None:
    database = _db(db_path)
    imported = 0
    batch = []
    with zipfile.ZipFile(zip_path) as archive:
        csv_name = archive.namelist()[0]
        with archive.open(csv_name) as raw_file:
            text_lines = (line.decode("utf-8-sig", errors="replace") for line in raw_file)
            reader = csv.DictReader(text_lines, delimiter=";")
            for row in reader:
                batch.append(normalize_camara_ceap_archive_row(row))
                if len(batch) >= batch_size:
                    imported += database.upsert_expenses(batch)
                    batch.clear()
            if batch:
                imported += database.upsert_expenses(batch)

    database.record_sync_run(
        job="import:camara-ceap-zip",
        source="camara",
        status="success",
        records_count=imported,
        metadata={"zip_path": str(zip_path), "batch_size": batch_size},
    )
    typer.echo(f"despesas importadas: {imported}")
    _echo_db_summary(database)


@collect_app.command("camara-deputados")
def collect_camara_deputados(
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 20,
) -> None:
    database = _db(db_path)
    payload = list_deputados(limit=limit)
    rows = payload.get("dados", [])
    normalized = [normalize_camara_deputado(row) for row in rows]
    count = database.upsert_parlamentarians(normalized)
    database.upsert_raw_payload(
        source="camara",
        kind="deputados",
        external_id=f"limit-{limit}",
        payload=payload,
    )
    database.record_sync_run(
        job="collect:camara-deputados",
        source="camara",
        status="success",
        records_count=count,
        metadata={"limit": limit},
    )
    typer.echo(f"parlamentares gravados: {count}")
    _echo_db_summary(database)


@collect_app.command("parlamentares-full")
def collect_parlamentares_full(
    db_path: DbPathOption = None,
    camara_page_size: Annotated[int, typer.Option("--camara-page-size", min=1, max=100)] = 100,
) -> None:
    database = _db(db_path)

    deputados_rows = list_all_deputados(page_size=camara_page_size)
    deputados = [normalize_camara_deputado(row) for row in deputados_rows]
    deputados_count = database.upsert_parlamentarians(deputados)
    database.upsert_raw_payload(
        source="camara",
        kind="deputados-full",
        external_id="ativos",
        payload=deputados_rows,
    )
    database.record_sync_run(
        job="collect:parlamentares-full:camara",
        source="camara",
        status="success",
        records_count=deputados_count,
        metadata={"page_size": camara_page_size},
    )

    senado_payload = list_senadores_atual()
    senadores_rows = _safe_senadores_list(senado_payload)
    senadores = [normalize_senado_senador(row) for row in senadores_rows]
    senadores_count = database.upsert_parlamentarians(senadores)
    database.upsert_raw_payload(
        source="senado",
        kind="senadores-full",
        external_id="ativos",
        payload=senado_payload,
    )
    database.record_sync_run(
        job="collect:parlamentares-full:senado",
        source="senado",
        status="success",
        records_count=senadores_count,
        metadata={},
    )

    typer.echo(f"deputados gravados: {deputados_count}")
    typer.echo(f"senadores gravados: {senadores_count}")
    typer.echo(f"total parlamentares ativos gravados: {deputados_count + senadores_count}")
    _echo_db_summary(database)


@collect_app.command("camara-despesas")
def collect_camara_despesas(
    deputado_id: Annotated[int, typer.Option("--deputado-id")],
    db_path: DbPathOption = None,
    ano: Annotated[int, typer.Option("--ano", min=2008)] = 2024,
    limit: Annotated[int, typer.Option("--limit", min=1, max=1000)] = 100,
) -> None:
    database = _db(db_path)
    payload = list_deputado_despesas(deputado_id=deputado_id, ano=ano, limit=limit)
    rows = payload.get("dados", [])
    normalized = [normalize_camara_despesa(row, deputado_id) for row in rows]
    count = database.upsert_expenses(normalized)
    database.upsert_raw_payload(
        source="camara",
        kind="despesas",
        external_id=f"{deputado_id}-{ano}",
        payload=payload,
    )
    database.record_sync_run(
        job="collect:camara-despesas",
        source="camara",
        status="success",
        records_count=count,
        metadata={"deputado_id": deputado_id, "ano": ano, "limit": limit},
    )
    typer.echo(f"despesas gravadas: {count}")
    _echo_db_summary(database)


@collect_app.command("camara-proposicoes")
def collect_camara_proposicoes(
    deputado_id: Annotated[int, typer.Option("--deputado-id")],
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 50,
) -> None:
    database = _db(db_path)
    payload = list_deputado_proposicoes(deputado_id=deputado_id, limit=limit)
    rows = payload.get("dados", [])
    normalized = [normalize_camara_proposicao(row) for row in rows]
    count = database.upsert_propositions(normalized)
    database.upsert_raw_payload(
        source="camara",
        kind="proposicoes-deputado",
        external_id=str(deputado_id),
        payload=payload,
    )
    database.record_sync_run(
        job="collect:camara-proposicoes",
        source="camara",
        status="success",
        records_count=count,
        metadata={"deputado_id": deputado_id, "limit": limit},
    )
    typer.echo(f"proposicoes gravadas: {count}")
    _echo_db_summary(database)


@collect_app.command("camara-proposicoes-ano")
def collect_camara_proposicoes_ano(
    ano: Annotated[int, typer.Option("--ano", min=1900)],
    db_path: DbPathOption = None,
    page_size: Annotated[int, typer.Option("--page-size", min=1, max=100)] = 100,
    start_page: Annotated[int, typer.Option("--start-page", min=1)] = 1,
    max_pages: Annotated[int, typer.Option("--max-pages", min=1, max=1000)] = 10,
) -> None:
    database = _db(db_path)
    total = 0
    pages = 0
    for page in range(start_page, start_page + max_pages):
        payload = list_proposicoes_by_year(ano=ano, limit=page_size, page=page)
        rows = payload.get("dados", [])
        if not rows:
            break
        total += database.upsert_propositions(
            [normalize_camara_proposicao(row) for row in rows]
        )
        database.upsert_raw_payload(
            source="camara",
            kind="proposicoes-ano",
            external_id=f"{ano}-pagina-{page}",
            payload=payload,
        )
        pages += 1
        if len(rows) < page_size:
            break

    database.record_sync_run(
        job="collect:camara-proposicoes-ano",
        source="camara",
        status="success",
        records_count=total,
        metadata={
            "ano": ano,
            "page_size": page_size,
            "start_page": start_page,
            "pages": pages,
        },
    )
    typer.echo(f"proposicoes camara gravadas: {total}")
    typer.echo(f"paginas processadas: {pages}")
    _echo_db_summary(database)


@collect_app.command("camara-lote")
def collect_camara_lote(
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=50)] = 10,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    ano_despesas: Annotated[int, typer.Option("--ano-despesas", min=2008)] = 2024,
    proposicoes_limit: Annotated[int, typer.Option("--proposicoes-limit", min=1, max=100)] = 25,
    despesas_limit: Annotated[int, typer.Option("--despesas-limit", min=1, max=1000)] = 25,
) -> None:
    database = _db(db_path)
    parlamentares = database.list_parliamentarians(source="camara", limit=limit, offset=offset)
    proposicoes_count = 0
    despesas_count = 0

    for parlamentar in parlamentares:
        deputado_id = int(parlamentar["external_id"])
        detail = get_deputado_detail(deputado_id=deputado_id)
        orgaos = list_deputado_orgaos(deputado_id=deputado_id)
        frentes = list_deputado_frentes(deputado_id=deputado_id)
        database.upsert_raw_payload(
            source="camara",
            kind="deputado-perfil",
            external_id=str(deputado_id),
            payload={"detail": detail, "orgaos": orgaos, "frentes": frentes},
        )

        proposicoes_payload = list_deputado_proposicoes(
            deputado_id=deputado_id,
            limit=proposicoes_limit,
        )
        proposicoes_rows = proposicoes_payload.get("dados", [])
        proposicoes_count += database.upsert_propositions(
            [normalize_camara_proposicao(row) for row in proposicoes_rows]
        )
        database.upsert_raw_payload(
            source="camara",
            kind="deputado-proposicoes",
            external_id=str(deputado_id),
            payload=proposicoes_payload,
        )

        despesas_payload = list_deputado_despesas(
            deputado_id=deputado_id,
            ano=ano_despesas,
            limit=despesas_limit,
        )
        despesas_rows = despesas_payload.get("dados", [])
        despesas_count += database.upsert_expenses(
            [normalize_camara_despesa(row, deputado_id) for row in despesas_rows]
        )
        database.upsert_raw_payload(
            source="camara",
            kind="deputado-despesas",
            external_id=f"{deputado_id}-{ano_despesas}",
            payload=despesas_payload,
        )

    database.record_sync_run(
        job="collect:camara-lote",
        source="camara",
        status="success",
        records_count=len(parlamentares),
        metadata={
            "limit": limit,
            "offset": offset,
            "ano_despesas": ano_despesas,
            "proposicoes": proposicoes_count,
            "despesas": despesas_count,
        },
    )
    typer.echo(f"perfis camara processados: {len(parlamentares)}")
    typer.echo(f"proposicoes gravadas: {proposicoes_count}")
    typer.echo(f"despesas gravadas: {despesas_count}")
    _echo_db_summary(database)


@collect_app.command("camara-proposicoes-full-lote")
def collect_camara_proposicoes_full_lote(
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 25,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
) -> None:
    database = _db(db_path)
    proposicoes = database.list_propositions(source="camara", limit=limit, offset=offset)
    failure_count = 0

    for proposicao in proposicoes:
        proposicao_id = int(proposicao["external_id"])
        try:
            detail = get_proposicao_detail(proposicao_id=proposicao_id)
            autores = list_proposicao_autores(proposicao_id=proposicao_id)
            temas = list_proposicao_temas(proposicao_id=proposicao_id)
            tramitacoes = list_proposicao_tramitacoes(proposicao_id=proposicao_id)
            database.upsert_raw_payload(
                source="camara",
                kind="proposicao-full",
                external_id=str(proposicao_id),
                payload={
                    "detail": detail,
                    "autores": autores,
                    "temas": temas,
                    "tramitacoes": tramitacoes,
                },
            )
        except Exception as exc:  # noqa: BLE001 - record per-proposition source failure.
            failure_count += 1
            database.upsert_raw_payload(
                source="camara",
                kind="proposicao-error",
                external_id=str(proposicao_id),
                payload={
                    "id": proposicao_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )

    database.record_sync_run(
        job="collect:camara-proposicoes-full-lote",
        source="camara",
        status="partial" if failure_count else "success",
        records_count=len(proposicoes),
        metadata={"limit": limit, "offset": offset, "failures": failure_count},
    )
    typer.echo(f"proposicoes camara detalhadas: {len(proposicoes)}")
    typer.echo(f"falhas registradas: {failure_count}")
    _echo_db_summary(database)


@collect_app.command("senado-senadores")
def collect_senado_senadores(
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 81,
) -> None:
    database = _db(db_path)
    payload = list_senadores_atual()
    rows = _safe_senadores_list(payload)[:limit]
    normalized = [normalize_senado_senador(row) for row in rows]
    count = database.upsert_parlamentarians(normalized)
    database.upsert_raw_payload(
        source="senado",
        kind="senadores",
        external_id=f"limit-{limit}",
        payload=payload,
    )
    database.record_sync_run(
        job="collect:senado-senadores",
        source="senado",
        status="success",
        records_count=count,
        metadata={"limit": limit},
    )
    typer.echo(f"parlamentares gravados: {count}")
    _echo_db_summary(database)


@collect_app.command("senado-processos")
def collect_senado_processos(
    db_path: DbPathOption = None,
    senador_codigo: Annotated[int | None, typer.Option("--senador-codigo")] = None,
    termo: Annotated[str | None, typer.Option("--termo")] = None,
    data_inicio: Annotated[str | None, typer.Option("--data-inicio")] = None,
    data_fim: Annotated[str | None, typer.Option("--data-fim")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=1000)] = 100,
) -> None:
    if senador_codigo is not None:
        rows = list_processos_by_parlamentar(codigo=senador_codigo)
        external_id = f"senador-{senador_codigo}"
        metadata: dict[str, Any] = {"senador_codigo": senador_codigo}
    elif termo:
        rows = list_processos_by_termo(termo=termo, data_inicio=data_inicio, data_fim=data_fim)
        external_id = f"termo-{termo}"
        metadata = {"termo": termo, "data_inicio": data_inicio, "data_fim": data_fim}
    else:
        raise typer.BadParameter("Informe --senador-codigo ou --termo.")

    database = _db(db_path)
    sample = rows[:limit]
    normalized = [normalize_senado_processo(row) for row in sample]
    count = database.upsert_propositions(normalized)
    database.upsert_raw_payload(
        source="senado",
        kind="processos",
        external_id=external_id,
        payload=sample,
    )
    database.record_sync_run(
        job="collect:senado-processos",
        source="senado",
        status="success",
        records_count=count,
        metadata={**metadata, "limit": limit, "raw_count": len(rows)},
    )
    typer.echo(f"proposicoes gravadas: {count}")
    _echo_db_summary(database)


@collect_app.command("senado-lote")
def collect_senado_lote(
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=50)] = 10,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    processos_limit: Annotated[int, typer.Option("--processos-limit", min=1, max=1000)] = 100,
) -> None:
    database = _db(db_path)
    senadores = database.list_parliamentarians(source="senado", limit=limit, offset=offset)
    proposicoes_count = 0
    failure_count = 0

    for senador in senadores:
        codigo = int(senador["external_id"])
        try:
            comissoes = list_senador_comissoes(codigo=codigo)
            database.upsert_raw_payload(
                source="senado",
                kind="senador-comissoes",
                external_id=str(codigo),
                payload=comissoes,
            )

            processos = list_processos_by_parlamentar(codigo=codigo)[:processos_limit]
            proposicoes_count += database.upsert_propositions(
                [normalize_senado_processo(row) for row in processos]
            )
            database.upsert_raw_payload(
                source="senado",
                kind="senador-processos",
                external_id=str(codigo),
                payload=processos,
            )
        except Exception as exc:  # noqa: BLE001 - keep batch moving and record source failure.
            failure_count += 1
            database.upsert_raw_payload(
                source="senado",
                kind="senador-error",
                external_id=str(codigo),
                payload={
                    "codigo": codigo,
                    "nome": senador["name"],
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )

    database.record_sync_run(
        job="collect:senado-lote",
        source="senado",
        status="partial" if failure_count else "success",
        records_count=len(senadores),
        metadata={
            "limit": limit,
            "offset": offset,
            "processos": proposicoes_count,
            "failures": failure_count,
        },
    )
    typer.echo(f"perfis senado processados: {len(senadores)}")
    typer.echo(f"proposicoes gravadas: {proposicoes_count}")
    typer.echo(f"falhas registradas: {failure_count}")
    _echo_db_summary(database)


@collect_app.command("senado-ceaps")
def collect_senado_ceaps(
    db_path: DbPathOption = None,
    ano: Annotated[int, typer.Option("--ano", min=2008)] = 2024,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100000)] = 1000,
) -> None:
    database = _db(db_path)
    rows = list_senador_ceaps(ano=ano)[:limit]
    normalized = [normalize_senado_ceaps(row) for row in rows]
    count = database.upsert_expenses(normalized)
    database.upsert_raw_payload(
        source="senado",
        kind="ceaps",
        external_id=str(ano),
        payload=rows,
    )
    database.record_sync_run(
        job="collect:senado-ceaps",
        source="senado",
        status="success",
        records_count=count,
        metadata={"ano": ano, "limit": limit},
    )
    typer.echo(f"despesas gravadas: {count}")
    _echo_db_summary(database)


@collect_app.command("senado-processos-full-lote")
def collect_senado_processos_full_lote(
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 25,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
) -> None:
    database = _db(db_path)
    processos = database.list_propositions(source="senado_processo", limit=limit, offset=offset)
    failure_count = 0

    for processo in processos:
        processo_id = int(processo["external_id"])
        try:
            payload = get_processo_detail(processo_id=processo_id)
            database.upsert_raw_payload(
                source="senado",
                kind="processo-full",
                external_id=str(processo_id),
                payload=payload,
            )
        except Exception as exc:  # noqa: BLE001 - record per-process source failure.
            failure_count += 1
            database.upsert_raw_payload(
                source="senado",
                kind="processo-error",
                external_id=str(processo_id),
                payload={
                    "id": processo_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )

    database.record_sync_run(
        job="collect:senado-processos-full-lote",
        source="senado",
        status="partial" if failure_count else "success",
        records_count=len(processos),
        metadata={"limit": limit, "offset": offset, "failures": failure_count},
    )
    typer.echo(f"processos senado detalhados: {len(processos)}")
    typer.echo(f"falhas registradas: {failure_count}")
    _echo_db_summary(database)


@discover_app.command("camara-deputados")
def discover_camara_deputados(
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 10,
) -> None:
    payload = list_deputados(limit=limit)
    rows = payload.get("dados", [])
    normalized = [normalize_camara_deputado(row).model_dump() for row in rows]
    _print_summary("Camara - deputados atuais", len(rows), normalized, "camara_deputados")


@discover_app.command("camara-deputado-full")
def discover_camara_deputado_full(
    deputado_id: Annotated[int, typer.Option("--deputado-id")],
) -> None:
    detail = get_deputado_detail(deputado_id=deputado_id).get("dados", {})
    orgaos = list_deputado_orgaos(deputado_id=deputado_id).get("dados", [])
    frentes = list_deputado_frentes(deputado_id=deputado_id).get("dados", [])
    payload = {
        "detail": detail,
        "orgaos_count": len(orgaos),
        "orgaos_sample": orgaos[:5],
        "frentes_count": len(frentes),
        "frentes_sample": frentes[:5],
    }
    path = write_snapshot(f"camara_deputado_full_{deputado_id}", payload)
    typer.echo("Camara - perfil parlamentar expandido")
    typer.echo(f"- detalhe campos: {len(detail.keys())}")
    typer.echo(f"- orgaos: {len(orgaos)}")
    typer.echo(f"- frentes: {len(frentes)}")
    typer.echo(f"- snapshot: {path}")


@discover_app.command("camara-despesas")
def discover_camara_despesas(
    deputado_id: Annotated[int, typer.Option("--deputado-id")],
    ano: Annotated[int, typer.Option("--ano", min=2008)] = 2024,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 10,
) -> None:
    payload = list_deputado_despesas(deputado_id=deputado_id, ano=ano, limit=limit)
    rows = payload.get("dados", [])
    normalized = [normalize_camara_despesa(row, deputado_id).model_dump() for row in rows]
    _print_summary(
        "Camara - despesas CEAP",
        len(rows),
        normalized,
        f"camara_despesas_{deputado_id}_{ano}",
    )


@discover_app.command("camara-proposicoes")
def discover_camara_proposicoes(
    deputado_id: Annotated[int, typer.Option("--deputado-id")],
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 10,
) -> None:
    payload = list_deputado_proposicoes(deputado_id=deputado_id, limit=limit)
    rows = payload.get("dados", [])
    normalized = [normalize_camara_proposicao(row).model_dump() for row in rows]
    _print_summary(
        "Camara - proposicoes por deputado",
        len(rows),
        normalized,
        f"camara_proposicoes_{deputado_id}",
    )


@discover_app.command("camara-proposicao-full")
def discover_camara_proposicao_full(
    proposicao_id: Annotated[int, typer.Option("--proposicao-id")],
) -> None:
    detail = get_proposicao_detail(proposicao_id=proposicao_id).get("dados", {})
    autores = list_proposicao_autores(proposicao_id=proposicao_id).get("dados", [])
    temas = list_proposicao_temas(proposicao_id=proposicao_id).get("dados", [])
    tramitacoes = list_proposicao_tramitacoes(proposicao_id=proposicao_id).get("dados", [])
    payload = {
        "detail": detail,
        "autores_count": len(autores),
        "autores_sample": autores[:5],
        "temas_count": len(temas),
        "temas_sample": temas[:10],
        "tramitacoes_count": len(tramitacoes),
        "tramitacoes_sample": tramitacoes[:10],
    }
    path = write_snapshot(f"camara_proposicao_full_{proposicao_id}", payload)
    typer.echo("Camara - proposicao expandida")
    typer.echo(f"- detalhe campos: {len(detail.keys())}")
    typer.echo(f"- autores: {len(autores)}")
    typer.echo(f"- temas: {len(temas)}")
    typer.echo(f"- tramitacoes: {len(tramitacoes)}")
    typer.echo(f"- snapshot: {path}")


@discover_app.command("senado-senadores")
def discover_senado_senadores(
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 10,
) -> None:
    payload = list_senadores_atual()
    rows = _safe_senadores_list(payload)[:limit]
    normalized = [normalize_senado_senador(row).model_dump() for row in rows]
    _print_summary("Senado - senadores em exercicio", len(rows), normalized, "senado_senadores")


@discover_app.command("senado-comissoes")
def discover_senado_comissoes(
    senador_codigo: Annotated[int, typer.Option("--senador-codigo")],
) -> None:
    payload = list_senador_comissoes(codigo=senador_codigo)
    path = write_snapshot(f"senado_comissoes_{senador_codigo}", payload)
    typer.echo(f"Senado - comissoes do senador {senador_codigo}")
    typer.echo(f"- snapshot: {path}")


@discover_app.command("senado-autorias")
def discover_senado_autorias(
    senador_codigo: Annotated[int, typer.Option("--senador-codigo")],
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 10,
) -> None:
    payload = list_senador_autorias(codigo=senador_codigo)
    materias = payload.get("MateriasAutoriaParlamentar", {})
    parlamentar = materias.get("Parlamentar", {})
    autorias = parlamentar.get("Autorias", {}).get("Autoria", [])
    if isinstance(autorias, dict):
        autorias = [autorias]
    rows = autorias[:limit]
    normalized = [normalize_senado_autoria(row).model_dump() for row in rows]
    metadata = materias.get("Metadados", {})
    _print_summary(
        f"Senado - autorias do senador {senador_codigo}",
        len(rows),
        normalized,
        f"senado_autorias_{senador_codigo}",
        metadata=metadata,
    )


@discover_app.command("senado-processos")
def discover_senado_processos(
    senador_codigo: Annotated[int | None, typer.Option("--senador-codigo")] = None,
    termo: Annotated[str | None, typer.Option("--termo")] = None,
    data_inicio: Annotated[str | None, typer.Option("--data-inicio")] = None,
    data_fim: Annotated[str | None, typer.Option("--data-fim")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=500)] = 10,
) -> None:
    if senador_codigo is not None:
        rows = list_processos_by_parlamentar(codigo=senador_codigo)
        snapshot_name = f"senado_processos_senador_{senador_codigo}"
        title = f"Senado - processos do senador {senador_codigo}"
    elif termo:
        rows = list_processos_by_termo(termo=termo, data_inicio=data_inicio, data_fim=data_fim)
        safe_term = termo.replace(" ", "_")[:30]
        snapshot_name = f"senado_processos_{safe_term}"
        title = f"Senado - processos por termo '{termo}'"
    else:
        raise typer.BadParameter("Informe --senador-codigo ou --termo.")

    sample = rows[:limit]
    normalized = [normalize_senado_processo(row).model_dump() for row in sample]
    _print_summary(title, len(rows), normalized, snapshot_name, metadata={"sample_limit": limit})


@discover_app.command("senado-processo-full")
def discover_senado_processo_full(
    processo_id: Annotated[int, typer.Option("--processo-id")],
) -> None:
    payload = get_processo_detail(processo_id=processo_id)
    path = write_snapshot(f"senado_processo_full_{processo_id}", payload)
    typer.echo("Senado - processo expandido")
    typer.echo(f"- campos raiz: {len(payload.keys())}")
    typer.echo(f"- snapshot: {path}")


@discover_app.command("senado-ceaps")
def discover_senado_ceaps(
    ano: Annotated[int, typer.Option("--ano", min=2008)] = 2024,
    limit: Annotated[int, typer.Option("--limit", min=1, max=1000)] = 10,
) -> None:
    rows = list_senador_ceaps(ano=ano)[:limit]
    normalized = [normalize_senado_ceaps(row).model_dump() for row in rows]
    _print_summary("Senado - despesas CEAPS", len(rows), normalized, f"senado_ceaps_{ano}")


@app.command("status")
def status_cmd(db_path: DbPathOption = None) -> None:
    """Mostra o estado atual da base de dados e progresso da coleta."""
    database = _db(db_path)
    summary = database.summary()
    sync_runs = database.list_recent_sync_runs(limit=5)

    typer.echo("=== Painel do Legislativo - Status da Coleta ===\n")

    typer.echo("--- Tabelas Principais ---")
    typer.echo(f"  Parlamentares:       {summary['parlamentarians']:>8,}")
    typer.echo(f"  Proposicoes:         {summary['propositions']:>8,}")
    typer.echo(f"  Despesas (CEAP):     {summary['expenses']:>8,}")
    typer.echo(f"  Raw payloads:        {summary['raw_payloads']:>8,}")

    typer.echo("\n--- Referencia ---")
    typer.echo(f"  Tipos de proposicao: {summary['proposition_types']:>8,}")
    typer.echo(f"  Partidos:            {summary['parties']:>8,}")
    typer.echo(f"  Legislaturas:        {summary['legislatures']:>8,}")
    typer.echo(f"  Orgaos:              {summary['organs']:>8,}")

    typer.echo("\n--- Relacionamentos ---")
    typer.echo(f"  Mandatos:               {summary['parliamentarian_mandates']:>8,}")
    typer.echo(f"  Membros de orgaos:      {summary['organ_memberships']:>8,}")
    typer.echo(f"  Frentes parlamentares:  {summary['parliamentary_fronts']:>8,}")
    typer.echo(f"  Membros de frentes:     {summary['front_memberships']:>8,}")
    typer.echo(f"  Autores de proposicoes: {summary['proposition_authors']:>8,}")
    typer.echo(f"  Temas de proposicoes:   {summary['proposition_themes']:>8,}")
    typer.echo(f"  Tramitacoes:            {summary['proposition_trackings']:>8,}")

    if summary["parlamentarians"] > 0:
        enriched_camara = len(database.get_enriched_parliamentarian_ids("camara"))
        enriched_senado = len(database.get_enriched_parliamentarian_ids("senado"))
        typer.echo("\n--- Cobertura ---")
        typer.echo(f"  Deputados enriquecidos:  {enriched_camara:>8,}")
        typer.echo(f"  Senadores enriquecidos:  {enriched_senado:>8,}")

    if summary["propositions"] > 0:
        pending = database.count_unenriched_propositions(source="camara")
        pending_recent = database.count_unenriched_propositions(source="camara", min_ano=2024)
        typer.echo(f"  Proposicoes sem detalhe: {pending:>8,}  (recentes: {pending_recent:,})")

    typer.echo("\n--- Ultimas sincronizacoes ---")
    if sync_runs:
        for run in sync_runs:
            typer.echo(f"  {run['finished_at'][:19]}  {run['job'][:45]:45s}  {run['status']:8s}  {run['records_count']:>8,}")
    else:
        typer.echo("  (nenhuma)")

    typer.echo(f"\nBanco: {database.path}")


@app.command("supabase-schema")
def supabase_schema_cmd(
    output: Annotated[str, typer.Option("--output", "-o")] = "supabase_schema.sql",
) -> None:
    """Gera o schema SQL para criar as tabelas no Supabase."""
    from pathlib import Path

    schema_path = Path(__file__).resolve().parent / "supabase_schema.sql"
    dest = Path(output)
    dest.write_text(schema_path.read_text(encoding="utf-8"), encoding="utf-8")
    typer.echo(f"Schema salvo em: {dest}")


@discover_app.command("referencia-tipos")
def discover_referencia_tipos(
    limit: Annotated[int, typer.Option("--limit", min=1, max=544)] = 20,
) -> None:
    """Descobre os tipos de proposicao disponiveis na Camara."""
    payload = list_referencia_tipos_proposicao()
    rows = payload.get("dados", [])[:limit]
    for r in rows:
        typer.echo(f"{r['sigla']:6s} ({r['cod']:3s}) - {r['nome']}")


@discover_app.command("camara-partidos")
def discover_camara_partidos(
    limit: Annotated[int, typer.Option("--limit", min=1, max=200)] = 30,
) -> None:
    """Descobre os partidos politicos na Camara."""
    payload = list_partidos(limit=limit)
    rows = payload.get("dados", [])
    for r in rows:
        typer.echo(f"{r['sigla']:12s} - {r.get('nome', '')}")


@discover_app.command("camara-legislaturas")
def discover_camara_legislaturas() -> None:
    """Lista todas as legislaturas."""
    payload = list_legislatures(limit=100)
    for leg in payload.get("dados", []):
        typer.echo(f"Leg {leg['id']}: {leg.get('dataInicio','')} -> {leg.get('dataFim','')}")


@discover_app.command("camara-orgaos")
def discover_camara_orgaos(
    limit: Annotated[int, typer.Option("--limit", min=1, max=500)] = 20,
) -> None:
    """Descobre orgaos/comissoes da Camara."""
    from legislativo_backend.collectors.camara import list_orgaos

    payload = list_orgaos(limit=limit)
    for o in payload.get("dados", []):
        typer.echo(f"{o['sigla']:12s} - {o.get('nome',''):50s} [{o.get('tipoOrgao','')}]")


@discover_app.command("camara-eventos")
def discover_camara_eventos(
    ano: Annotated[int, typer.Option("--ano")] = 2025,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 10,
) -> None:
    """Descobre eventos na Camara."""
    from legislativo_backend.collectors.camara import list_eventos

    payload = list_eventos(ano=ano, limit=limit)
    for e in payload.get("dados", []):
        typer.echo(f"{e.get('dataHoraInicio','')} - {e.get('descricaoTipo','')} - {e.get('descricao','')[:80]}")


@discover_app.command("camara-votacoes")
def discover_camara_votacoes(
    ano: Annotated[int, typer.Option("--ano")] = 2025,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 10,
) -> None:
    """Descobre votações na Camara."""
    from legislativo_backend.collectors.camara import list_votacoes

    payload = list_votacoes(ano=ano, limit=limit)
    for v in payload.get("dados", []):
        typer.echo(f"{v.get('data','')} - {v.get('proposicaoObjeto','')[:60]} - {'APROV' if v.get('aprovacao') else 'REJEIT'}")


@discover_app.command("senador-full")
def discover_senador_full(
    codigo: Annotated[int, typer.Option("--codigo")],
) -> None:
    """Descobre TUDO sobre um senador (mandatos, discursos, etc)."""
    from legislativo_backend.collectors.senado import (
        list_senador_cargos,
        list_senador_discursos,
        list_senador_filiacoes,
        list_senador_liderancas,
        list_senador_mandatos,
        list_senador_relatorias,
    )

    typer.echo(f"\n=== Mandatos de {codigo} ===")
    try:
        m = list_senador_mandatos(codigo)
        typer.echo(str(m)[:500])
    except Exception as e:
        typer.echo(f"Erro: {e}")

    typer.echo(f"\n=== Filiacoes de {codigo} ===")
    try:
        f = list_senador_filiacoes(codigo)
        typer.echo(str(f)[:500])
    except Exception as e:
        typer.echo(f"Erro: {e}")

    typer.echo(f"\n=== Discursos de {codigo} ===")
    try:
        d = list_senador_discursos(codigo)
        typer.echo(str(d)[:500])
    except Exception as e:
        typer.echo(f"Erro: {e}")

    typer.echo(f"\n=== Relatorias de {codigo} ===")
    try:
        r = list_senador_relatorias(codigo)
        typer.echo(str(r)[:500])
    except Exception as e:
        typer.echo(f"Erro: {e}")

    typer.echo(f"\n=== Cargos de {codigo} ===")
    try:
        c = list_senador_cargos(codigo)
        typer.echo(str(c)[:500])
    except Exception as e:
        typer.echo(f"Erro: {e}")

    typer.echo(f"\n=== Liderancas de {codigo} ===")
    try:
        ld = list_senador_liderancas(codigo)
        typer.echo(str(ld)[:500])
    except Exception as e:
        typer.echo(f"Erro: {e}")


@pipeline_app.command("reference")
def pipeline_reference(
    db_path: DbPathOption = None,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Coleta dados de referencia: partidos, legislaturas, tipos de proposicao."""
    from legislativo_backend.pipeline import collect_reference_data
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None
    if supabase_sync and not supabase.enabled:
        typer.echo("Supabase nao configurado. Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY.")
        raise typer.Exit(1)

    counts = collect_reference_data(database, supabase)
    for name, count in counts.items():
        typer.echo(f"{name}: {count}")
    _echo_db_summary(database)


@pipeline_app.command("parlamentares")
def pipeline_parlamentares(
    db_path: DbPathOption = None,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Coleta todos os parlamentares (deputados + senadores)."""
    from legislativo_backend.pipeline import collect_all_parliamentarians
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None

    counts = collect_all_parliamentarians(database, supabase)
    for name, count in counts.items():
        typer.echo(f"{name}: {count}")
    _echo_db_summary(database)


@pipeline_app.command("enrich-camara")
def pipeline_enrich_camara(
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=513)] = 10,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    anos_despesas: Annotated[str, typer.Option("--anos-despesas")] = "2025,2024,2023",
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Enriquece dados de deputados: orgaos, frentes, proposicoes, despesas."""
    from legislativo_backend.pipeline import enrich_deputados
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None
    anos = [int(a.strip()) for a in anos_despesas.split(",")]

    counts = enrich_deputados(database, supabase, limit=limit, offset=offset, anos_despesas=anos)
    for name, count in counts.items():
        typer.echo(f"{name}: {count}")
    _echo_db_summary(database)


@pipeline_app.command("enrich-senado")
def pipeline_enrich_senado(
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=81)] = 10,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Enriquece dados de senadores: comissoes, processos."""
    from legislativo_backend.pipeline import enrich_senadores
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None

    counts = enrich_senadores(database, supabase, limit=limit, offset=offset)
    for name, count in counts.items():
        typer.echo(f"{name}: {count}")
    _echo_db_summary(database)


@pipeline_app.command("enrich-proposicoes")
def pipeline_enrich_proposicoes(
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 25,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Enriquece proposicoes: autores, temas, tramitacoes (por offset fixo)."""
    from legislativo_backend.pipeline import enrich_proposicoes_camara
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None

    counts = enrich_proposicoes_camara(database, supabase, limit=limit, offset=offset)
    for name, count in counts.items():
        typer.echo(f"{name}: {count}")
    _echo_db_summary(database)


@pipeline_app.command("discursos")
def pipeline_discursos(
    db_path: DbPathOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=81)] = 10,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Coleta discursos de senadores e popula tabela discursos."""
    from legislativo_backend.pipeline import collect_discursos_senado
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None

    counts = collect_discursos_senado(database, supabase, limit=limit, offset=offset)
    for name, count in counts.items():
        typer.echo(f"{name}: {count}")
    _echo_db_summary(database)


@pipeline_app.command("enrich-props-incr")
def pipeline_enrich_props_incr(
    db_path: DbPathOption = None,
    batch_size: Annotated[int, typer.Option("--batch-size", min=1, max=100)] = 25,
    max_batches: Annotated[int | None, typer.Option("--max-batches", min=1)] = None,
    min_ano: Annotated[int | None, typer.Option("--min-ano")] = None,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Enriquece proposicoes NAO processadas (incremental, prioriza recentes). Resume automatico."""
    from legislativo_backend.pipeline import enrich_proposicoes_incremental
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None

    pending = database.count_unenriched_propositions(source="camara", min_ano=min_ano)
    typer.echo(f"Proposicoes pendentes: {pending}")
    counts = enrich_proposicoes_incremental(
        database, supabase, batch_size=batch_size, max_batches=max_batches, min_ano=min_ano,
    )
    for name, count in counts.items():
        typer.echo(f"{name}: {count}")
    remaining = database.count_unenriched_propositions(source="camara", min_ano=min_ano)
    typer.echo(f"Restantes apos esta execucao: {remaining}")
    _echo_db_summary(database)


@pipeline_app.command("deputado")
def pipeline_deputado(
    deputado_id: Annotated[int, typer.Option("--deputado-id")],
    db_path: DbPathOption = None,
    anos_despesas: Annotated[str, typer.Option("--anos-despesas")] = "2025,2024,2023",
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Coleta TUDO sobre UM deputado especifico."""
    from legislativo_backend.pipeline import enrich_deputado_completo
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None
    anos = [int(a.strip()) for a in anos_despesas.split(",")]
    result = enrich_deputado_completo(database, deputado_id, supabase, anos)
    for k, v in result.items():
        typer.echo(f"{k}: {v}")
    _echo_db_summary(database)


@pipeline_app.command("senador")
def pipeline_senador(
    codigo: Annotated[int, typer.Option("--codigo")],
    db_path: DbPathOption = None,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Coleta TUDO sobre UM senador especifico."""
    from legislativo_backend.pipeline import enrich_senador_completo
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None
    result = enrich_senador_completo(database, codigo, supabase)
    for k, v in result.items():
        typer.echo(f"{k}: {v}")
    _echo_db_summary(database)


@pipeline_app.command("proposicao")
def pipeline_proposicao(
    proposicao_id: Annotated[int, typer.Option("--proposicao-id")],
    db_path: DbPathOption = None,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Coleta TUDO sobre UMA proposicao especifica."""
    from legislativo_backend.pipeline import enrich_proposicao_completa
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None
    result = enrich_proposicao_completa(database, proposicao_id, supabase=supabase)
    for k, v in result.items():
        typer.echo(f"{k}: {v}")
    _echo_db_summary(database)


@pipeline_app.command("bulk-ceap")
def pipeline_bulk_ceap(
    anos: Annotated[str, typer.Option("--anos")] = "2025",
    db_path: DbPathOption = None,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Baixa CSV ZIP da CEAP por ano e importa todas as despesas (bulk)."""
    from legislativo_backend.pipeline import collect_bulk_ceap_year
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None
    anos_list = [int(a.strip()) for a in anos.split(",")]
    for ano in anos_list:
        typer.echo(f"\n=== Importando CEAP {ano} ===")
        result = collect_bulk_ceap_year(database, ano, supabase)
        for k, v in result.items():
            typer.echo(f"  {k}: {v}")
    _echo_db_summary(database)


@pipeline_app.command("bulk-year")
def pipeline_bulk_year(
    anos: Annotated[str, typer.Option("--anos")] = "2025",
    db_path: DbPathOption = None,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Baixa ano completo: proposicoes + temas + autores (3 arquivos bulk)."""
    from legislativo_backend.pipeline import collect_bulk_complete_year
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None
    anos_list = [int(a.strip()) for a in anos.split(",")]
    for ano in anos_list:
        typer.echo(f"\n=== Importando ano {ano} ===")
        result = collect_bulk_complete_year(database, ano, supabase)
        for k, v in result.items():
            typer.echo(f"  {k}: {v}")
    _echo_db_summary(database)


@pipeline_app.command("full")
def pipeline_full(
    db_path: DbPathOption = None,
    batch_size: Annotated[int, typer.Option("--batch-size", min=1, max=50)] = 10,
    anos_despesas: Annotated[str, typer.Option("--anos-despesas")] = "2025,2024,2023",
    anos_proposicoes: Annotated[str | None, typer.Option("--anos-proposicoes")] = None,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Pipeline completo: referencias, parlamentares, enriquecimento, proposicoes."""
    from legislativo_backend.pipeline import full_pipeline
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None
    if supabase_sync and not supabase.enabled:
        typer.echo("Supabase nao configurado. Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY.")
        raise typer.Exit(1)

    anos = [int(a.strip()) for a in anos_despesas.split(",")]
    anos_p = [int(a.strip()) for a in anos_proposicoes.split(",")] if anos_proposicoes else None

    results = full_pipeline(database, supabase, batch_size=batch_size, anos_despesas=anos, anos_proposicoes=anos_p)

    typer.echo("\n=== Pipeline Completo ===")
    typer.echo(f"Tempo: {results['elapsed_seconds']}s")
    for section, data in results.items():
        if isinstance(data, dict):
            typer.echo(f"\n{section}:")
            for k, v in data.items():
                typer.echo(f"  {k}: {v}")
    _echo_db_summary(database)


@pipeline_app.command("votacoes")
def pipeline_votacoes(
    ano: Annotated[int, typer.Option("--ano", min=2000)] = 2025,
    db_path: DbPathOption = None,
    supabase_sync: Annotated[bool, typer.Option("--supabase")] = False,
) -> None:
    """Coleta votacoes e votos de um ano da Camara."""
    from legislativo_backend.pipeline import collect_votacoes_ano
    from legislativo_backend.supabase_client import SupabaseClient

    database = _db(db_path)
    supabase = SupabaseClient() if supabase_sync else None
    if supabase_sync and not supabase.enabled:
        typer.echo("Supabase nao configurado.")
        raise typer.Exit(1)

    result = collect_votacoes_ano(database, ano, source="camara", supabase=supabase)
    typer.echo(f"\nVotacoes {ano}: {result['votacoes']} sessoes, {result['votos']} votos, {result.get('errors', 0)} erros")
    _echo_db_summary(database)


if __name__ == "__main__":
    app()
