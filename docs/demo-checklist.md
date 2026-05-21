# Checklist de ensayo para la presentación final

Ejecuta estos pasos **en la misma máquina** donde presentarás, **antes** del día del jurado.

## 1. Arranque en limpio (volumenes nuevos)

1. Copia entorno si aún no existe: `cp .env.example .env`
2. Apaga y borra volúmenes: `docker compose down -v`
3. Construye y levanta: `docker compose up --build -d`
4. Verifica proceso: `docker compose ps` (cinco servicios `running`; el shipper puede seguir esperando `cowrie.json` hasta que haya tráfico al honeypot)

## 2. Sin SSH: datos visibles en el dashboard

1. Espera ~30–60 s a que la API marque healthy (Compose ya tiene healthchecks).
2. Abre el dashboard en `http://localhost:$DASHBOARD_PORT` (por defecto `8501`).
3. Comprueba que aparezca el estado del sistema: API OK, PostgreSQL OK y conteo de eventos.
4. Comprueba que **métricas y tabla no estén vacías** si Postgres se inicializó de cero (`db/init.sql` inserta filas de muestra en el primer bootstrap del volumen).
5. Revisa los filtros laterales: rango de fechas, tipo de evento, IP y usuario.
6. Opcional rápido: `make demo-smoke` (requiere API arriba; ver `Makefile`).

## 3. Demo dinámica: nueva actividad constante

1. En otra terminal ejecuta: `make demo-traffic`.
2. El script genera eventos por `POST /events` usando `SHIPPER_TOKEN`.
3. El dashboard se refresca cada ~5 s; deberías ver aumentar `total_events`, cambiar la tabla y moverse las gráficas.
4. Para una prueba corta: `DEMO_TRAFFIC_DURATION=60 DEMO_TRAFFIC_INTERVAL=3 make demo-traffic`.

## 4. Con SSH real: nueva actividad en ≤60 s

1. Ejecuta: `ssh root@localhost -p 2222` (acepta fingerprint; cualquier contraseña falsa cuenta).
2. Cowrie creará `var/log/cowrie/cowrie.json` dentro de su volumen; el shipper lo leerá y hará POST protegido a `/events`.
3. Tras hasta **unos 60 segundos** (y hasta **~5 s** de caché en Streamlit), revisa el dashboard o `curl -s "http://localhost:8000/stats"`.
4. Deberías ver **aumento** en `total_events` o filas nuevas respecto al paso 2.

## Notas

- Si el dashboard “no cambia” al instante: espera el auto-refresh o usa refresco del navegador.
- Si no hay filas de muestra: probablemente reutilizas un volumen Postgres antiguo; usa `docker compose down -v` y vuelve al paso 1.
- Si `POST /events` responde 401/403: revisa que `SHIPPER_TOKEN` sea igual en `api`, `shipper` y el entorno desde donde corres `make demo-traffic`.
