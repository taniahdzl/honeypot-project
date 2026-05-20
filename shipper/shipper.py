#!/usr/bin/env python3
"""
Lee el log JSON de Cowrie línea por línea y envía cada evento a la API FastAPI.
Pensado para demo con Docker Compose: comparte volumen cowrie_var con Cowrie.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

API_URL = os.environ.get("API_URL", "http://api:8000").rstrip("/")
SHIPPER_TOKEN = os.environ.get("SHIPPER_TOKEN", "demo-secret-token")
COWRIE_JSON_LOG = os.environ.get(
    "COWRIE_JSON_LOG",
    "/cowrie/cowrie-git/var/log/cowrie/cowrie.json",
)
STATE_PATH = Path(
    os.environ.get("SHIPPER_STATE_DIR", "/data")
) / "cowrie_shipper.offset"
SHIPPER_BATCH_SLEEP = float(os.environ.get("SHIPPER_BATCH_SLEEP", "0.05"))


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_event_time(ts: Any) -> str | None:
    if ts is None:
        return None
    s = str(ts).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        return dt.isoformat()
    except ValueError:
        return None


def extract_src_ip(data: dict[str, Any]) -> str | None:
    ip = data.get("src_ip")
    if isinstance(ip, str) and ip:
        return ip
    # Algunos eventos llevan dirección como dict
    for key in ("peer_ip",):
        v = data.get(key)
        if isinstance(v, str) and v:
            return v
    peer = data.get("peer")
    if isinstance(peer, dict):
        for k in ("ip", "host"):
            pv = peer.get(k)
            if isinstance(pv, str) and pv:
                return pv
    return None


def cowrie_line_to_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_time": parse_event_time(data.get("timestamp")),
        "src_ip": extract_src_ip(data),
        "event_type": data.get("eventid"),
        "username": data.get("username"),
        "password": data.get("password"),
        "command": data.get("input"),
        "raw_json": data,
    }
    return payload


def post_json(path: str, body: dict[str, Any], timeout: int = 15) -> None:
    encoded = json.dumps(body, default=str).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}{path}",
        data=encoded,
        headers={
            "Authorization": f"Bearer {SHIPPER_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout):  # noqa: S310
        return


def wait_for_health(max_wait: float = 300.0, interval: float = 3.0) -> None:
    deadline = time.time() + max_wait
    req = urllib.request.Request(f"{API_URL}/health", method="GET")
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310
                if r.status == 200:
                    log("Shipper: API disponible (/health OK).")
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        log("Shipper: esperando API…")
        time.sleep(interval)
    log("Shipper: la API no respondió a tiempo.")
    sys.exit(1)


def wait_for_logfile(max_wait: float = 3600.0, interval: float = 5.0) -> Path:
    path = Path(COWRIE_JSON_LOG)
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if path.is_file():
            log(f"Shipper: log Cowrie encontrado en {path}.")
            return path
        log(f"Shipper: esperando archivo {path} (¿algún SSH al honeypot aún?).")
        time.sleep(interval)
    log("Shipper: no apareció cowrie.json; revisa rutas/volumen compartido.")
    sys.exit(1)


def read_offset() -> int:
    try:
        return int(STATE_PATH.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_offset(offset: int) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(str(offset), encoding="utf-8")


def main() -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    wait_for_health()
    path = wait_for_logfile()

    offset = read_offset()

    log(f"Shipper: iniciando desde offset={offset}")

    backoff = 1.0
    while True:
        try:
            if not path.is_file():
                time.sleep(5.0)
                continue

            current_size = path.stat().st_size
            if offset > current_size:
                offset = 0
                save_offset(offset)

            with path.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(offset)
                while True:
                    pos_before = f.tell()
                    line = f.readline()
                    if not line:
                        break
                    pos_after = f.tell()
                    line = line.strip()
                    if not line.startswith("{"):
                        save_offset(pos_after)
                        offset = pos_after
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        save_offset(pos_after)
                        offset = pos_after
                        continue
                    if not isinstance(data, dict):
                        save_offset(pos_after)
                        offset = pos_after
                        continue
                    body = cowrie_line_to_payload(data)
                    try:
                        post_json("/events", body)
                        save_offset(pos_after)
                        offset = pos_after
                        backoff = max(1.0, backoff * 0.5)
                    except urllib.error.HTTPError as e:
                        log(f"Shipper: POST /events HTTP {e.code} — reintentando.")
                        try:
                            f.seek(pos_before)
                        except OSError:
                            offset = pos_before
                            save_offset(offset)
                            break
                        time.sleep(backoff)
                        backoff = min(60.0, backoff * 2)
                    except (urllib.error.URLError, TimeoutError) as e:
                        log(f"Shipper: error de red ({e}); reintentando.")
                        try:
                            f.seek(pos_before)
                        except OSError:
                            offset = pos_before
                            save_offset(offset)
                            break
                        time.sleep(backoff)
                        backoff = min(60.0, backoff * 2)

            time.sleep(SHIPPER_BATCH_SLEEP)
        except OSError as e:
            log(f"Shipper: error de archivo ({e}); reintentando en 5s.")
            time.sleep(5)


if __name__ == "__main__":
    main()
