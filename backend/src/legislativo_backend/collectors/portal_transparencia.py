from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from legislativo_backend.http import fetch_json

load_dotenv()

BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"

API_KEY: str | None = None


def _get_api_key() -> str:
    global API_KEY
    if API_KEY is None:
        API_KEY = os.getenv("PORTAL_TRANSPARENCIA_API_KEY", "")
    if not API_KEY:
        raise RuntimeError(
            "PORTAL_TRANSPARENCIA_API_KEY nao configurada. "
            "Obtenha em https://portaldatransparencia.gov.br/api-de-dados"
        )
    return API_KEY


def _headers() -> dict[str, str]:
    return {"chave-api-dados": _get_api_key()}


def list_emendas(
    pagina: int = 1,
    codigo_parlamentar: int | None = None,
    ano: int | None = None,
    uf: str | None = None,
) -> dict[str, Any]:
    """Lista emendas parlamentares com filtros opcionais."""
    params: dict[str, Any] = {"pagina": pagina}
    if codigo_parlamentar:
        params["codigoParlamentar"] = codigo_parlamentar
    if ano:
        params["ano"] = ano
    if uf:
        params["uf"] = uf
    return fetch_json(f"{BASE_URL}/emendas", params=params)


def list_all_emendas(
    ano: int | None = None,
    uf: str | None = None,
    page_size: int = 15,
) -> list[dict[str, Any]]:
    """Coleta TODAS as emendas disponiveis, paginando automaticamente."""
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = list_emendas(pagina=page, ano=ano, uf=uf)
        if isinstance(payload, list):
            rows.extend(payload)
            if len(payload) < page_size:
                break
            page += 1
        elif isinstance(payload, dict):
            items = payload.get("data") or payload.get("dados") or []
            if not items:
                break
            rows.extend(items)
            if len(items) < page_size:
                break
            page += 1
        else:
            break
    return rows


def list_emendas_por_parlamentar(
    codigo_parlamentar: int,
    ano: int | None = None,
) -> list[dict[str, Any]]:
    """Coleta emendas de um parlamentar especifico."""
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = list_emendas(
            pagina=page,
            codigo_parlamentar=codigo_parlamentar,
            ano=ano,
        )
        if isinstance(payload, list):
            rows.extend(payload)
            if len(payload) < 15:
                break
            page += 1
        elif isinstance(payload, dict):
            items = payload.get("data") or payload.get("dados") or []
            if not items:
                break
            rows.extend(items)
            page += 1
        else:
            break
    return rows
