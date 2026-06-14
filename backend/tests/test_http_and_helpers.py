"""Testes para utilidades de HTTP/coleta introduzidas nas melhorias:
ensure_list, thread-safety do RateLimiter e o decorator de retry de downloads.
"""

from __future__ import annotations

import threading
import time

import httpx
import pytest

from legislativo_backend.http import RateLimiter, download_retry
from legislativo_backend.normalizers import ensure_list


def test_ensure_list_wraps_dict_into_single_item():
    assert ensure_list({"a": 1}) == [{"a": 1}]


def test_ensure_list_passes_through_lists():
    assert ensure_list([1, 2]) == [1, 2]


def test_ensure_list_handles_none_and_scalars():
    assert ensure_list(None) == []
    assert ensure_list("texto") == []


def test_rate_limiter_enforces_minimum_interval():
    limiter = RateLimiter(min_interval=0.05)
    start = time.monotonic()
    limiter.wait()  # primeira chamada nao espera
    limiter.wait()  # segunda deve esperar ~0.05s
    elapsed = time.monotonic() - start
    assert elapsed >= 0.05


def test_rate_limiter_is_thread_safe():
    # Com lock, N chamadas concorrentes nunca rodam "ao mesmo tempo":
    # o tempo total deve respeitar (N-1) * intervalo.
    limiter = RateLimiter(min_interval=0.02)
    threads = [threading.Thread(target=limiter.wait) for _ in range(5)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.02 * 4 * 0.8  # margem para jitter de scheduling


def test_download_retry_reattempts_on_transport_error():
    calls = {"n": 0}

    @download_retry
    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.TransportError("boom")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_download_retry_reraises_after_exhausting_attempts():
    @download_retry
    def always_fails() -> None:
        raise httpx.TimeoutException("nope")

    with pytest.raises(httpx.TimeoutException):
        always_fails()
