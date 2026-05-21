import os
import time
from typing import Any

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000").rstrip("/")
DASHBOARD_REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "5"))

st.title("Dashboard Honeypot")
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
st.sidebar.caption(f"Actualiza cada {DASHBOARD_REFRESH_SECONDS} s")

REQUEST_TIMEOUT = 30.0


def rerun_dashboard() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


@st.cache_data(ttl=5)
def fetch_events(limit: int = 200) -> pd.DataFrame:
    url = f"{API_BASE_URL}/events"
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        r = client.get(url, params={"limit": limit})
        r.raise_for_status()
        payload = r.json()
    rows = payload.get("events", [])
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


@st.cache_data(ttl=5)
def fetch_stats() -> dict[str, Any]:
    url = f"{API_BASE_URL}/stats"
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.json()


try:
    stats = fetch_stats()
    cols = st.columns(2)
    cols[0].metric("Eventos totales", stats.get("total_events", 0))
    cols[1].metric("Eventos últimas 24 h", stats.get("recent_24h", 0))
except Exception as e:
    st.error(f"No se pudo conectar con la API ({API_BASE_URL}): {e}")
    st.stop()

df = fetch_events(200)

st.subheader("Eventos recientes")
if df.empty:
    st.info("Todavía no hay eventos. Conéctate al honeypot: ssh root@localhost -p 2222")
else:
    st.dataframe(df, use_container_width=True)

    top_ips_payload = stats.get("top_ips") or []
    if top_ips_payload:
        st.subheader("Top IPs (resumen desde API)")
        tip = pd.DataFrame(top_ips_payload)
        st.bar_chart(tip.set_index("src_ip")["count"])

    st.subheader("Tipos de evento")
    ett = pd.DataFrame(stats.get("top_event_types", []))
    if not ett.empty:
        st.bar_chart(ett.set_index("event_type")["count"])
    elif "event_type" in df:
        st.bar_chart(df["event_type"].fillna("unknown").value_counts().head(10))

if auto_refresh:
    time.sleep(DASHBOARD_REFRESH_SECONDS)
    rerun_dashboard()
