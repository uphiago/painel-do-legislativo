from __future__ import annotations

import threading
import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "painel-do-legislativo/0.1 discovery collector",
}

CAMARA_RATE_LIMIT = 4.0   # seconds between requests (max 15/min, safe)
SENADO_RATE_LIMIT = 0.5  # seconds between requests (max 10/sec, generous buffer)
BULK_DOWNLOAD_LIMIT = 2.0  # seconds between bulk file downloads


class RateLimiter:
    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._last_call = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        # Lock garante que dois threads nao concluam o check-and-sleep
        # simultaneamente e acabem violando o intervalo minimo.
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


_camara_limiter = RateLimiter(CAMARA_RATE_LIMIT)
_senado_limiter = RateLimiter(SENADO_RATE_LIMIT)
_bulk_limiter = RateLimiter(BULK_DOWNLOAD_LIMIT)


def wait_bulk() -> None:
    """Rate-limit para downloads de arquivos grandes (bulk)."""
    _bulk_limiter.wait()


def _get_limiter(url: str) -> RateLimiter:
    if "camara.leg.br" in url:
        return _camara_limiter
    return _senado_limiter


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError)),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
def fetch_json(url: str, params: dict[str, Any] | None = None) -> Any:
    limiter = _get_limiter(url)
    limiter.wait()
    with httpx.Client(headers=DEFAULT_HEADERS, timeout=30, follow_redirects=True) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


# Retry reutilizavel para downloads de arquivos grandes (proposicoes anuais,
# CEAP zip). Janelas de espera maiores que o fetch_json normal porque sao
# arquivos de dezenas de MB sujeitos a quedas de conexao.
download_retry = retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
