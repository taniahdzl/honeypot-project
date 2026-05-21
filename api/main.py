import json
import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text

DB_USER = os.getenv("POSTGRES_USER", "honeyuser")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "honeypass")
DB_NAME = os.getenv("POSTGRES_DB", "honeypot")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
SHIPPER_TOKEN = os.getenv("SHIPPER_TOKEN", "demo-secret-token")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Honeypot API")


class EventIn(BaseModel):
    event_time: Optional[datetime] = None
    src_ip: Optional[str] = None
    event_type: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    command: Optional[str] = None
    raw_json: Optional[dict] = None
    source_hash: Optional[str] = None


def verify_shipper_token(authorization: Optional[str]) -> None:
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=401,
            detail="Formato de Authorization inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(token, SHIPPER_TOKEN):
        raise HTTPException(status_code=403, detail="Token inválido")


@app.get("/")
def root():
    return {"message": "API funcionando"}


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "api": "ok", "database": "ok"}


@app.get("/events")
def get_events(limit: int = Query(50, ge=1, le=500)):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, event_time, src_ip, event_type, username, password, command
                FROM cowrie_events
                ORDER BY id DESC
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().all()
    return {"events": [dict(r) for r in rows]}


@app.get("/events/{event_id}")
def get_event_by_id(event_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT id, event_time, src_ip, event_type, username, password, command, raw_json
                FROM cowrie_events
                WHERE id = :event_id
            """),
            {"event_id": event_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return {"event": dict(row)}


@app.post("/events")
def create_event(event: EventIn, authorization: Optional[str] = Header(default=None)):
    verify_shipper_token(authorization)

    raw_json_literal = None
    if event.raw_json is not None:
        raw_json_literal = json.dumps(event.raw_json, default=str)

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO cowrie_events (
                    event_time, src_ip, event_type, username, password, command, raw_json, source_hash
                )
                VALUES (
                    :event_time, :src_ip, :event_type, :username, :password, :command,
                    CAST(:raw_json AS JSONB), :source_hash
                )
                ON CONFLICT (source_hash) WHERE source_hash IS NOT NULL DO NOTHING
            """),
            {
                "event_time": event.event_time,
                "src_ip": event.src_ip,
                "event_type": event.event_type,
                "username": event.username,
                "password": event.password,
                "command": event.command,
                "raw_json": raw_json_literal,
                "source_hash": event.source_hash,
            },
        )
    return {"message": "evento insertado"}


@app.get("/stats")
def stats():
    with engine.connect() as conn:
        totals_row = conn.execute(
            text("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (
                        WHERE event_time IS NOT NULL
                          AND event_time >= NOW() - INTERVAL '24 hours'
                    ) AS recent_24h
                FROM cowrie_events
            """)
        ).mappings().first()
        tops_ip = conn.execute(
            text("""
                SELECT src_ip, COUNT(*) AS count
                FROM cowrie_events
                WHERE src_ip IS NOT NULL AND TRIM(src_ip) <> ''
                GROUP BY src_ip
                ORDER BY count DESC NULLS LAST
                LIMIT 10
            """)
        ).mappings().all()
        tops_type = conn.execute(
            text("""
                SELECT
                    COALESCE(NULLIF(TRIM(event_type), ''), 'unknown') AS event_type,
                    COUNT(*) AS count
                FROM cowrie_events
                GROUP BY 1
                ORDER BY count DESC
                LIMIT 15
            """)
        ).mappings().all()

    return {
        "total_events": int(totals_row["total"] or 0),
        "recent_24h": int(totals_row["recent_24h"] or 0),
        "top_ips": [dict(r) for r in tops_ip],
        "top_event_types": [dict(r) for r in tops_type],
    }
