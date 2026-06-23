from __future__ import annotations

import logging
import os
import threading as _threading
import time as _time
from typing import Any

import httpx
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"
PORTAL_RATE_LIMIT = 2.0  # req/segundo (conservador ~30/min)

API_KEY: str | None = None
_last_request = 0.0
_lock = _threading.Lock()


def _wait() -> None:
    global _last_request
    with _lock:
        elapsed = _time.monotonic() - _last_request
        if elapsed < PORTAL_RATE_LIMIT:
            _time.sleep(PORTAL_RATE_LIMIT - elapsed)
        _last_request = _time.monotonic()


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


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError)),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _fetch(url: str, params: dict[str, Any] | None = None) -> Any:
    _wait()
    headers = {
        "Accept": "application/json",
        "chave-api-dados": _get_api_key(),
    }
    with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


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
    return _fetch(f"{BASE_URL}/emendas", params=params)


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
