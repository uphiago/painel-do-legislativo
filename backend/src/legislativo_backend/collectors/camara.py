from __future__ import annotations

from typing import Any

from legislativo_backend.http import DEFAULT_HEADERS, download_retry, fetch_json, wait_bulk

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"


def list_deputados(limit: int = 10, page: int = 1) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/deputados",
        params={
            "itens": limit,
            "pagina": page,
            "ordem": "ASC",
            "ordenarPor": "nome",
        },
    )


def list_all_deputados(page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = list_deputados(limit=page_size, page=page)
        page_rows = payload.get("dados", [])
        rows.extend(page_rows)
        if len(page_rows) < page_size:
            return rows
        page += 1


def list_deputado_despesas(deputado_id: int, ano: int, limit: int = 10) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/deputados/{deputado_id}/despesas",
        params={
            "ano": ano,
            "itens": limit,
            "ordem": "ASC",
            "ordenarPor": "dataDocumento",
        },
    )


def list_deputado_proposicoes(deputado_id: int, limit: int = 10) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/proposicoes",
        params={
            "idDeputadoAutor": deputado_id,
            "itens": limit,
            "ordem": "DESC",
            "ordenarPor": "id",
        },
    )


def list_proposicoes_by_year(ano: int, limit: int = 100, page: int = 1) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/proposicoes",
        params={
            "ano": ano,
            "itens": limit,
            "pagina": page,
            "ordem": "DESC",
            "ordenarPor": "id",
        },
    )


def get_deputado_detail(deputado_id: int) -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/deputados/{deputado_id}")


def list_deputado_frentes(deputado_id: int) -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/deputados/{deputado_id}/frentes")


def list_deputado_orgaos(deputado_id: int) -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/deputados/{deputado_id}/orgaos")


def get_proposicao_detail(proposicao_id: int) -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/proposicoes/{proposicao_id}")


def list_proposicao_autores(proposicao_id: int) -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/proposicoes/{proposicao_id}/autores")


def list_proposicao_temas(proposicao_id: int) -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/proposicoes/{proposicao_id}/temas")


def list_proposicao_tramitacoes(proposicao_id: int) -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/proposicoes/{proposicao_id}/tramitacoes")


def list_partidos(limit: int = 100, page: int = 1) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/partidos",
        params={"itens": limit, "pagina": page, "ordem": "ASC", "ordenarPor": "sigla"},
    )


def get_partido_detail(partido_id: int) -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/partidos/{partido_id}")


def list_organs(limit: int = 100, page: int = 1) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/orgaos",
        params={"itens": limit, "pagina": page, "ordem": "ASC", "ordenarPor": "sigla"},
    )


def get_organ_detail(orgao_id: int) -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/orgaos/{orgao_id}")


def list_legislatures(limit: int = 100, page: int = 1) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/legislaturas",
        params={"itens": limit, "pagina": page},
    )


def get_proposicao_text(proposicao_id: int) -> str | None:
    data = get_proposicao_detail(proposicao_id)
    return data.get("dados", {}).get("urlInteiroTeor")


def list_referencia_tipos_proposicao() -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/referencias/tiposProposicao")


def list_deputado_eventos(deputado_id: int, limit: int = 50, page: int = 1) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/deputados/{deputado_id}/eventos",
        params={"itens": limit, "pagina": page},
    )


def list_all_deputado_proposicoes(deputado_id: int, page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = fetch_json(
            f"{BASE_URL}/proposicoes",
            params={
                "idDeputadoAutor": deputado_id,
                "itens": page_size,
                "pagina": page,
                "ordem": "DESC",
                "ordenarPor": "id",
            },
        )
        page_rows = payload.get("dados", [])
        rows.extend(page_rows)
        if len(page_rows) < page_size:
            break
        page += 1
    return rows


def list_all_deputado_despesas(deputado_id: int, ano: int, page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = fetch_json(
            f"{BASE_URL}/deputados/{deputado_id}/despesas",
            params={
                "ano": ano,
                "itens": page_size,
                "pagina": page,
                "ordem": "ASC",
                "ordenarPor": "dataDocumento",
            },
        )
        page_rows = payload.get("dados", [])
        rows.extend(page_rows)
        if len(page_rows) < page_size:
            break
        page += 1
    return rows


def list_all_proposicoes_by_year(ano: int, page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = list_proposicoes_by_year(ano=ano, limit=page_size, page=page)
        page_rows = payload.get("dados", [])
        rows.extend(page_rows)
        if len(page_rows) < page_size:
            break
        page += 1
    return rows


def list_all_orgaos(page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = list_organs(limit=page_size, page=page)
        page_rows = payload.get("dados", [])
        rows.extend(page_rows)
        if len(page_rows) < page_size:
            break
        page += 1
    return rows


def list_eventos(ano: int, limit: int = 100, page: int = 1) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/eventos",
        params={
            "dataInicio": f"{ano}-01-01",
            "dataFim": f"{ano}-12-31",
            "itens": limit,
            "pagina": page,
        },
    )


def list_all_eventos_by_year(ano: int, page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = list_eventos(ano=ano, limit=page_size, page=page)
        page_rows = payload.get("dados", [])
        rows.extend(page_rows)
        if len(page_rows) < page_size:
            break
        page += 1
    return rows


def list_votacoes(ano: int, limit: int = 100, page: int = 1) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/votacoes",
        params={
            "ano": ano,
            "itens": limit,
            "pagina": page,
        },
    )


def list_all_votacoes_by_year(ano: int, page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = list_votacoes(ano=ano, limit=page_size, page=page)
        page_rows = payload.get("dados", [])
        rows.extend(page_rows)
        if len(page_rows) < page_size:
            break
        page += 1
    return rows


def get_votacao_detail(votacao_id: int) -> dict[str, Any]:
    return fetch_json(f"{BASE_URL}/votacoes/{votacao_id}")


def list_votacoes_by_proposicao(proposicao_id: int, limit: int = 50, page: int = 1) -> dict[str, Any]:
    uri = f"{BASE_URL}/proposicoes/{proposicao_id}"
    return fetch_json(
        f"{BASE_URL}/votacoes",
        params={
            "uriProposicaoObjeto": uri,
            "itens": limit,
            "pagina": page,
        },
    )


def list_proposicoes_by_tipo_and_ano(
    sigla_tipo: str, ano: int, limit: int = 100, page: int = 1
) -> dict[str, Any]:
    return fetch_json(
        f"{BASE_URL}/proposicoes",
        params={
            "siglaTipo": sigla_tipo,
            "ano": ano,
            "itens": limit,
            "pagina": page,
            "ordem": "DESC",
            "ordenarPor": "id",
        },
    )


@download_retry
def download_proposicoes_arquivo(ano: int, formato: str = "json") -> list[dict[str, Any]]:
    """Baixa o arquivo anual completo de proposicoes do site da Camara."""
    import httpx

    wait_bulk()
    url = f"https://dadosabertos.camara.leg.br/arquivos/proposicoes/{formato}/proposicoes-{ano}.{formato}"
    resp = httpx.get(url, headers=DEFAULT_HEADERS, timeout=120, follow_redirects=True)
    resp.raise_for_status()
    raw = resp.json()
    if isinstance(raw, dict):
        return raw.get("dados", [])
    if isinstance(raw, list):
        return raw
    return []


@download_retry
def download_proposicoes_temas_arquivo(ano: int, formato: str = "json") -> list[dict[str, Any]]:
    import httpx

    wait_bulk()
    url = f"https://dadosabertos.camara.leg.br/arquivos/proposicoesTemas/{formato}/proposicoesTemas-{ano}.{formato}"
    resp = httpx.get(url, headers=DEFAULT_HEADERS, timeout=120, follow_redirects=True)
    resp.raise_for_status()
    raw = resp.json()
    if isinstance(raw, dict):
        return raw.get("dados", [])
    return raw if isinstance(raw, list) else []


@download_retry
def download_proposicoes_autores_arquivo(ano: int, formato: str = "json") -> list[dict[str, Any]]:
    import httpx

    url = f"https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/{formato}/proposicoesAutores-{ano}.{formato}"
    resp = httpx.get(url, headers=DEFAULT_HEADERS, timeout=120, follow_redirects=True)
    resp.raise_for_status()
    raw = resp.json()
    if isinstance(raw, dict):
        return raw.get("dados", [])
    return raw if isinstance(raw, list) else []


def download_ceap_csv_stream(ano: int) -> list[dict[str, Any]]:
    """Baixa e parseia o CSV ZIP da CEAP de um ano com streaming.

    Usa iter_content para nao carregar o ZIP inteiro em memoria.
    Retorna um generator-friendly wrapper que nao acumula todas as linhas.
    """
    import csv
    import io
    import zipfile

    import httpx

    wait_bulk()
    url = f"https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
    headers = {**DEFAULT_HEADERS, "Accept": "*/*"}
    resp = httpx.get(url, headers=headers, timeout=120, follow_redirects=True)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        csv_name = archive.namelist()[0]
        with archive.open(csv_name) as raw_file:
            text_lines = (line.decode("utf-8-sig", errors="replace") for line in raw_file)
            reader = csv.DictReader(text_lines, delimiter=";")
            return list(reader)


def stream_ceap_csv_rows(ano: int):
    """Generator que faz yield de cada linha do CSV ZIP sem carregar tudo em memoria."""
    import csv
    import io
    import zipfile

    import httpx

    url = f"https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
    headers = {**DEFAULT_HEADERS, "Accept": "*/*"}
    with httpx.stream("GET", url, headers=headers, timeout=120, follow_redirects=True) as resp:
        resp.raise_for_status()
        raw_bytes = io.BytesIO()
        for chunk in resp.iter_bytes(chunk_size=8192):
            raw_bytes.write(chunk)
        raw_bytes.seek(0)
        with zipfile.ZipFile(raw_bytes) as archive:
            csv_name = archive.namelist()[0]
            with archive.open(csv_name) as raw_file:
                text_lines = (line.decode("utf-8-sig", errors="replace") for line in raw_file)
                reader = csv.DictReader(text_lines, delimiter=";")
                yield from reader
