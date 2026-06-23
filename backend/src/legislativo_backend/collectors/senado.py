from __future__ import annotations

from typing import Any

from legislativo_backend.http import fetch_json

LEGIS_URL = "https://legis.senado.leg.br/dadosabertos"
ADMIN_URL = "https://adm.senado.gov.br/adm-dadosabertos/api/v1"


def list_senadores_atual() -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/lista/atual.json")


def list_senador_autorias(codigo: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/autorias.json")


def list_senador_comissoes(codigo: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/comissoes.json")


def list_processos_by_parlamentar(codigo: int) -> list[dict[str, Any]]:
    return fetch_json(f"{LEGIS_URL}/processo", params={"codigoParlamentarAutor": codigo, "v": 1})


def list_processos_by_termo(
    termo: str,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"termo": termo, "v": 1}
    if data_inicio:
        params["dataInicioApresentacao"] = data_inicio
    if data_fim:
        params["dataFimApresentacao"] = data_fim
    return fetch_json(f"{LEGIS_URL}/processo", params=params)


def get_processo_detail(processo_id: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/processo/{processo_id}", params={"v": 1})


def list_senador_ceaps(ano: int, limit: int | None = None) -> list[dict[str, Any]]:
    """Retorna CEAPS de um ano, paginando automaticamente. limit opcional para evitar fetch total."""
    return list_all_senador_ceaps(ano, limit=limit)


def list_all_senador_ceaps(ano: int, page_size: int = 1000, limit: int | None = None) -> list[dict[str, Any]]:
    """Coleta TODAS as CEAPS de um ano via paginacao real da API."""
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = fetch_json(
            f"{ADMIN_URL}/senadores/despesas_ceaps/{ano}",
            params={"pagina": page, "tamanhoPagina": page_size},
        )
        if isinstance(payload, list):
            rows.extend(payload)
            if limit and len(rows) >= limit:
                return rows[:limit]
            if len(payload) < page_size:
                break
            page += 1
        elif isinstance(payload, dict):
            items = payload.get("data") or payload.get("dados") or payload.get("items", [])
            if not items:
                break
            rows.extend(items if isinstance(items, list) else [items])
            if limit and len(rows) >= limit:
                return rows[:limit]
            total = payload.get("total") or payload.get("totalRegistros", 0)
            if len(rows) >= total:
                break
            page += 1
        else:
            break
    return rows


def list_senador_mandatos(codigo: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/mandatos.json")


def list_senador_filiacoes(codigo: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/filiacoes.json")


def list_processo_siglas() -> list[dict[str, Any]]:
    return fetch_json(f"{LEGIS_URL}/processo/siglas", params={"v": 1})


def list_processo_tipos_situacao() -> list[dict[str, Any]]:
    return fetch_json(f"{LEGIS_URL}/processo/tipos-situacao", params={"v": 1})


def list_comissoes(tipo: str = "colegiados") -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/comissao/lista/{tipo}.json")


def get_comissao_detail(codigo: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/comissao/{codigo}.json")


def list_senador_discursos(
    codigo: int, data_inicio: str | None = None, data_fim: str | None = None
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if data_inicio:
        params["dataInicio"] = data_inicio
    if data_fim:
        params["dataFim"] = data_fim
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/discursos.json", params=params)


def list_senador_relatorias(
    codigo: int,
    tramitando: str | None = None,
    sigla: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if tramitando:
        params["tramitando"] = tramitando
    if sigla:
        params["sigla"] = sigla
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/relatorias.json", params=params)


def list_senador_cargos(codigo: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/cargos.json")


def list_senador_liderancas(codigo: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/liderancas.json")


def list_senador_licencas(codigo: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/licencas.json")


def list_senador_profissao(codigo: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/profissao.json")


def list_senador_historico_academico(codigo: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/{codigo}/historicoAcademico.json")


def list_all_senadores_by_legislature(legislatura: int) -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/senador/lista/legislatura/{legislatura}.json")


def list_composicao_partidos() -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/composicao/lista/partidos.json")


def list_composicao_blocos() -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/composicao/lista/blocos.json")


def list_composicao_lideranca_sf() -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/composicao/lista/liderancaSF.json")


def list_composicao_mesa_sf() -> dict[str, Any]:
    return fetch_json(f"{LEGIS_URL}/composicao/mesaSF.json")


def list_votacoes_senado(
    data_inicio: str,
    data_fim: str,
    codigo_parlamentar: int | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"dataInicio": data_inicio, "dataFim": data_fim}
    if codigo_parlamentar:
        params["codigoParlamentar"] = codigo_parlamentar
    return fetch_json(f"{LEGIS_URL}/votacao", params=params)


def list_processo_documentos(
    processo_id: int, limit: int = 50
) -> dict[str, Any]:
    return fetch_json(
        f"{LEGIS_URL}/processo/documento",
        params={"idProcesso": processo_id, "v": 1},
    )


def list_processo_emendas(processo_id: int) -> dict[str, Any]:
    return fetch_json(
        f"{LEGIS_URL}/processo/emenda",
        params={"idProcesso": processo_id, "v": 1},
    )


def list_senador_ceaps_paginado(ano: int, page: int = 1, page_size: int = 1000) -> dict[str, Any]:
    return fetch_json(
        f"{ADMIN_URL}/senadores/despesas_ceaps/{ano}",
        params={"pagina": page, "tamanhoPagina": page_size},
    )
