import os
import time
from typing import Any, Optional

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000").rstrip("/")
DASHBOARD_REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "5"))
REQUEST_TIMEOUT = 30.0

st.set_page_config(page_title="Dashboard Honeypot", layout="wide")
st.title("Dashboard Honeypot")

auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
show_passwords = st.sidebar.checkbox("Mostrar contraseñas", value=False)
st.sidebar.caption(f"Actualiza cada {DASHBOARD_REFRESH_SECONDS} s")


def rerun_dashboard() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def mask_password(value: Any) -> Optional[str]:
    if value is None or pd.isna(value) or str(value) == "":
        return None
    password = str(value)
    if show_passwords:
        return password
    if len(password) <= 1:
        return "*"
    return f"{password[0]}{'*' * (len(password) - 1)}"


@st.cache_data(ttl=5)
def fetch_events(limit: int = 500) -> pd.DataFrame:
    url = f"{API_BASE_URL}/events"
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        r = client.get(url, params={"limit": limit})
        r.raise_for_status()
        payload = r.json()
    rows = payload.get("events", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "event_time" in df:
        df["event_time"] = pd.to_datetime(df["event_time"], utc=True, errors="coerce")
    return df


@st.cache_data(ttl=5)
def fetch_stats() -> dict[str, Any]:
    url = f"{API_BASE_URL}/stats"
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.json()


@st.cache_data(ttl=5)
def fetch_health() -> dict[str, Any]:
    url = f"{API_BASE_URL}/health"
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.json()


def non_empty_options(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df:
        return []
    values = df[column].dropna().astype(str)
    values = values[values.str.strip() != ""]
    return sorted(values.unique().tolist())


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    st.sidebar.subheader("Filtros")
    if "event_time" in filtered and filtered["event_time"].notna().any():
        min_date = filtered["event_time"].min().date()
        max_date = filtered["event_time"].max().date()
        selected_range = st.sidebar.date_input(
            "Rango de fechas",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start_date, end_date = selected_range
            start_ts = pd.Timestamp(start_date, tz="UTC")
            end_ts = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
            filtered = filtered[
                (filtered["event_time"] >= start_ts)
                & (filtered["event_time"] < end_ts)
            ]
    else:
        st.sidebar.caption("Sin fechas disponibles para filtrar.")

    for column, label in (
        ("event_type", "Tipo de evento"),
        ("src_ip", "IP origen"),
        ("username", "Usuario"),
    ):
        options = non_empty_options(filtered, column)
        if options:
            selected = st.sidebar.multiselect(label, options=options)
            if selected:
                filtered = filtered[filtered[column].astype(str).isin(selected)]
        else:
            st.sidebar.caption(f"Sin datos de {label.lower()}.")

    return filtered


def display_system_health(stats: dict[str, Any], health: Optional[dict[str, Any]]) -> None:
    st.subheader("Estado del sistema")
    cols = st.columns(3)
    if health:
        cols[0].success("API: OK")
        cols[1].success("PostgreSQL: OK")
    else:
        cols[0].error("API: Error")
        cols[1].error("PostgreSQL: Sin confirmar")

    total_events = int(stats.get("total_events", 0)) if stats else 0
    recent_events = int(stats.get("recent_24h", 0)) if stats else 0
    if total_events:
        cols[2].success(f"Eventos: {total_events} registrados ({recent_events} últimas 24 h)")
    else:
        cols[2].warning("Eventos: todavía sin registros")


def display_last_event(df: pd.DataFrame) -> None:
    st.subheader("Último evento recibido")
    if df.empty:
        st.info("Aún no hay eventos registrados.")
        return

    sort_column = "event_time" if "event_time" in df and df["event_time"].notna().any() else "id"
    last = df.sort_values(sort_column, ascending=False).iloc[0]
    cols = st.columns(3)
    cols[0].metric("Fecha/hora", format_value(last.get("event_time")))
    cols[1].metric("IP origen", format_value(last.get("src_ip")))
    cols[2].metric("Tipo", format_value(last.get("event_type")))

    cols = st.columns(3)
    cols[0].metric("Usuario", format_value(last.get("username")))
    cols[1].metric("Contraseña", format_value(mask_password(last.get("password"))))
    cols[2].metric("Comando", format_value(last.get("command")))


def format_value(value: Any) -> str:
    if value is None or pd.isna(value) or str(value) == "":
        return "N/D"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def display_charts(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No hay eventos para graficar con los filtros actuales.")
        return

    if "event_time" in df and df["event_time"].notna().sum() >= 2:
        st.subheader("Eventos por hora")
        series = (
            df.dropna(subset=["event_time"])
            .set_index("event_time")
            .resample("h")
            .size()
            .rename("eventos")
        )
        if series.empty or series.sum() == 0:
            st.info("No hay datos suficientes para graficar la serie temporal.")
        else:
            st.line_chart(series)
    else:
        st.info("No hay datos suficientes para graficar la serie temporal.")

    chart_cols = st.columns(2)
    if "src_ip" in df:
        top_ips = df["src_ip"].dropna().astype(str)
        top_ips = top_ips[top_ips.str.strip() != ""].value_counts().head(10)
        if not top_ips.empty:
            chart_cols[0].subheader("Top IPs")
            chart_cols[0].bar_chart(top_ips)

    if "event_type" in df:
        event_types = df["event_type"].fillna("unknown").astype(str)
        event_types = event_types[event_types.str.strip() != ""].value_counts().head(10)
        if not event_types.empty:
            chart_cols[1].subheader("Tipos de evento")
            chart_cols[1].bar_chart(event_types)


def table_for_display(df: pd.DataFrame) -> pd.DataFrame:
    display_df = df.copy()
    if "password" in display_df:
        display_df["password"] = display_df["password"].apply(mask_password)
    return display_df


stats: dict[str, Any] = {}
health: Optional[dict[str, Any]] = None
try:
    health = fetch_health()
    stats = fetch_stats()
    df = fetch_events(500)
except Exception as e:
    st.error(f"No se pudo conectar con la API ({API_BASE_URL}): {e}")
    display_system_health(stats, health)
    st.stop()

display_system_health(stats, health)
filtered_df = apply_filters(df) if not df.empty else df
display_last_event(df)

st.subheader("Eventos recientes")
if filtered_df.empty:
    st.info("Todavía no hay eventos para los filtros seleccionados.")
else:
    st.dataframe(table_for_display(filtered_df), width="stretch")

display_charts(filtered_df)

if auto_refresh:
    time.sleep(DASHBOARD_REFRESH_SECONDS)
    rerun_dashboard()
