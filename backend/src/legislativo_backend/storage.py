from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def write_snapshot(name: str, payload: Any) -> Path:
    output_dir = project_root() / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.json"
    envelope = {
        "source": name,
        "collected_at": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
