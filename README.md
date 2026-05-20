# 🍯 Plataforma de Telemetría para Honeypot

> Proyecto Final – Fuentes de Datos  
> Plataforma replicable y orientada a análisis de datos construida con **Cowrie**, **un servicio shipper de logs**, **Docker Compose**, **FastAPI**, **PostgreSQL** y **Streamlit**.

---

## 📌 Descripción general

Este proyecto simula un entorno controlado de engaño defensivo (*deception defense*): despliega un honeypot SSH/Telnet, captura la telemetría generada por interacciones sospechosas, la almacena en una base de datos relacional, la expone mediante una API REST y la visualiza en un dashboard interactivo.

El enfoque es académico y seguro: en lugar de herramientas ofensivas, el proyecto demuestra cómo la telemetría de ciberseguridad puede tratarse como una **fuente de datos** para extracción, transformación, almacenamiento y análisis.

---

## 🏗️ Arquitectura

```
Atacante / Bot
      │
      ▼
  [COWRIE]          Honeypot SSH/Telnet — genera logs JSON
      │
      ▼
  [SHIPPER]         Envía líneas cowrie.json → POST /events (mismo volumen que Cowrie)
      │
      ▼
  [FastAPI]         API REST — recibe, valida y persiste eventos
      │
      ▼
 [PostgreSQL]       Base de datos relacional — almacenamiento estructurado
      │
      ▼
  [Streamlit]       Dashboard — consume la API (métricas y tablas)
```

### Quantas de arquitectura

| Quantum | Servicios | Responsabilidad |
|---|---|---|
| **Captura** | Cowrie + shipper | Honeypot + envío automático de eventos JSON hacia la API |
| **Procesamiento** | FastAPI + PostgreSQL | Ingesta, validación y persistencia de eventos |
| **Visualización** | Streamlit | Consulta y presentación de métricas agregadas |

---

## 🧰 Stack tecnológico

| Tecnología | Rol |
|---|---|
| [Cowrie](https://github.com/cowrie/cowrie) | Honeypot de interacción media (SSH/Telnet) |
| [FastAPI](https://fastapi.tiangolo.com/) | Capa de API REST con documentación OpenAPI automática |
| [PostgreSQL 16](https://www.postgresql.org/) | Almacenamiento relacional de eventos (imagen en `compose.yaml`) |
| [Streamlit](https://streamlit.io/) | Dashboard de visualización interactiva |
| [Docker Compose](https://docs.docker.com/compose/) | Orquestación de todos los servicios |
| [Python 3.10+](https://www.python.org/) | Lenguaje base del backend y dashboard |

---

## 📁 Estructura del repositorio

```
honeypot-project/
├── api/
│   ├── Dockerfile
│   ├── main.py               # Endpoints FastAPI
│   ├── requirements.txt
│   └── tests/
│       └── test_main.py      # Pruebas con pytest
├── dashboard/
│   ├── Dockerfile
│   ├── app.py                # Dashboard Streamlit
│   └── requirements.txt
├── db/
│   └── init.sql              # Esquema + datos de muestra para la primera inicialización del volumen Postgres
├── shipper/
│   ├── Dockerfile           # Shipper ligero (solo stdlib Python)
│   └── shipper.py           # Lectura tipo tail de cowrie.json → API
├── docs/
│   ├── tableplus.md        # Conexión GUI a PostgreSQL
│   ├── adr/
│   │   ├── ADR-001-eleccion-honeypot-cowrie.md
│   │   ├── ADR-002-postgres-almacenamiento.md
│   │   ├── ADR-003-fastapi-capa-api.md
│   │   ├── ADR-004-streamlit-dashboard.md
│   │   └── ADR-005-shipper-ingesta-docker.md
│   ├── demo-checklist.md     # Lista de verificación ante el jurado
│   ├── openapi.json          # OpenAPI mantenido alineado con `api/main.py` (véase tabla `/docs`)
│   └── quantas.md            # Documento de architecture quantas
├── .github/
│   └── workflows/
│       └── ci.yml            # Pipeline de CI/CD con GitHub Actions
├── scripts/
│   └── demo-smoke.sh          # Humo HTTP contra `/health`, `/events`, `/stats`
├── Makefile                  # Target `demo-smoke`
├── compose.yaml
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚙️ Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) >= 24.x
- [Docker Compose](https://docs.docker.com/compose/install/) >= 2.x
- Git

> No se requiere Python ni ninguna otra dependencia instalada localmente. Todo corre dentro de los contenedores.

---

## 🚀 Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/victormbr-creator/honeypot-project.git
cd honeypot-project
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con los valores deseados:

```env
POSTGRES_USER=honeyuser
POSTGRES_PASSWORD=honeypass
POSTGRES_DB=honeypot
POSTGRES_HOST=db
POSTGRES_PORT=5432

API_PORT=8000
DASHBOARD_PORT=8501
```

### 3. Levantar todos los servicios

```bash
docker compose up -d
```

Esto levanta **cinco servicios**: Cowrie, shipper de logs, FastAPI, PostgreSQL y Streamlit. El shipper espera a que Cowrie cree `cowrie.json` (por ejemplo después del primer intento SSH al puerto 2222).

**Demo en vivo (presentación)**

1. `docker compose up -d`
2. Abre Streamlit (`http://localhost:8501`) — verás métricas y filas **de muestra** si el volumen de Postgres es nuevo.
3. En otra terminal: `make demo-traffic`. Durante unos 10 minutos se generan eventos controlados cada ~4 s para que el dashboard cambie en vivo.
4. Opcional: `ssh root@localhost -p 2222` (contraseña falsa bastan). En unos segundos nuevos eventos reales de Cowrie aparecen por el shipper → API → mismo dashboard tras refresco automático (~5 s).
5. Opcional — API: `curl -s http://localhost:8000/stats | python -m json.tool`

Si ya usaste el proyecto antes y la base está vacía o sin muestras: `docker compose down -v` y vuelve a levantar (borra datos locales).

Lista paso a paso para ensayar el día del jurado: [`docs/demo-checklist.md`](docs/demo-checklist.md).

### 4. Humo rápido de la API (opcional)

Con los contenedores arriba y **API_PORT=8000** en el host:

```bash
make demo-smoke
```

Equivale a `GET /health`, `GET /events?limit=1` y `GET /stats`. El mensaje final del script recuerda que **`cowrie.json` puede aparecer sólo después del primer intento SSH** al honeypot.

Para una demo dinámica y repetible de ~10 minutos:

```bash
make demo-traffic
```

Este script inserta telemetría controlada por la API local para que Streamlit muestre cambios constantes sin depender de intentos manuales o de herramientas externas. Puedes ajustar duración e intervalo así:

```bash
DEMO_TRAFFIC_DURATION=300 DEMO_TRAFFIC_INTERVAL=3 make demo-traffic
```

### 5. Verificar que todo esté corriendo

```bash
docker compose ps
```

Deberías ver los **cinco** contenedores con estado `running` (Cowrie, shipper, API, Postgres, dashboard). El shipper puede mostrar mensajes “esperando cowrie.json” hasta el primer contacto al honeypot.

---

## 🌐 Acceso a los servicios

| Servicio | URL | Descripción |
|---|---|---|
| **FastAPI** | http://localhost:8000 | API REST |
| **Swagger UI** | http://localhost:8000/docs | Documentación interactiva OpenAPI |
| **ReDoc** | http://localhost:8000/redoc | Documentación alternativa |
| **Streamlit** | http://localhost:8501 | Dashboard de telemetría |
| **Cowrie SSH** | `localhost:2222` | Puerto honeypot (¡no es un servidor real!) |
| **PostgreSQL** | `localhost:<POSTGRES_PORT>` | Base de datos (TablePlus, psql, etc.) |

---

## 🔌 PostgreSQL con TablePlus (u otros clientes GUI)

Guía detallada: [`docs/tableplus.md`](docs/tableplus.md).

Resumen rápido (usuario con permisos del `.env`; puerto desde `POSTGRES_PORT`):

- Host `127.0.0.1`, base `POSTGRES_DB`, usuario `POSTGRES_USER`, contraseña `POSTGRES_PASSWORD`.
- SSL habitual en Docker local: **desactivado** salvo que tú configures TLS.
- **Usuario sólo lectura** tras volumen fresco: `honeypot_readonly` / `honeypass_ro` (documentado también en `.env.example`; encaja demos sin tocar tablas desde la sala).

Si no conecta: Postgres no levantado, puerto distinto ocupado en el host o firewall institucional; ver Troubleshooting más abajo.

---

## 📡 Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Mensaje de estado de la API |
| `GET` | `/health` | Healthcheck del sistema |
| `GET` | `/events` | Lista eventos (query `limit`, por defecto 50). Respuesta: `{"events":[...]}` |
| `GET` | `/events/{id}` | Detalle por `id` (incluye `raw_json` si existe). Respuesta: `{"event":{...}}` o HTTP 404 |
| `POST` | `/events` | Ingresar un nuevo evento (usado por el shipper) |
| `GET` | `/stats` | `total_events`, `recent_24h`, `top_ips`, `top_event_types` |

> La especificación en [`docs/openapi.json`](docs/openapi.json) se mantiene **alineada a mano** con `api/main.py` (fuente canónica: código + `/docs` en tiempo de ejecución). Actualiza OpenAPI cuando cambien rutas o formas de respuesta.

Ejemplo rápido de detalle:

```bash
curl -s http://localhost:8000/events/1
```

---

## 🧪 Pruebas

Las pruebas se ubican en `api/tests/` y se ejecutan con `pytest`:

```bash
# Ejecutar pruebas localmente
python -m pip install -r api/requirements.txt pytest httpx
POSTGRES_HOST=127.0.0.1 PYTHONPATH=api:. pytest api/tests shipper/tests -v
```

Las pruebas de API que consultan PostgreSQL se omiten si la base de datos no está levantada; para ejecutarlas completas, inicia la demo con `docker compose up -d db` o `docker compose up -d` antes de correr `pytest`.

Las pruebas también se corren automáticamente en cada `push` a `main` mediante GitHub Actions (ver `.github/workflows/ci.yml`).

---

## 🔄 CI/CD

El proyecto incluye un pipeline de integración continua configurado con **GitHub Actions**.

**Se ejecuta automáticamente cuando:**
- Se hace `push` a la rama `main`
- Se abre un Pull Request hacia `main`

**Qué hace el pipeline:**
1. Hace checkout del código
2. Configura Python 3.10
3. Instala dependencias
4. Ejecuta las pruebas con `pytest`

Ver configuración completa en [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## 🎬 Demo rápida (simulación de ataque)

Para ver el sistema en acción, puedes simular un atacante intentando conectarse al honeypot:

```bash
# Intento de conexión SSH al honeypot (contraseña incorrecta a propósito)
ssh root@localhost -p 2222
# Prueba contraseñas débiles: 123456, password, admin, root
```

Cowrie registrará la sesión, el shipper (`shipper/` en Docker) enviará el evento a FastAPI, y en unos segundos aparecerá reflejado en el dashboard de Streamlit en `http://localhost:8501` (consulta datos vía API con caché breve).

---

## Troubleshooting (aula / laboratorio)

- **TablePlus: “could not connect” / timeout**: comprueba `docker compose ps` (servicio `db`), que `localhost` usa el mismo `POSTGRES_PORT` que en `.env`, y que no tienes otro Postgres ocupando ese puerto. Desactiva SSL para el perfil local.
- **Sin filas “de muestra” en Streamlit tras `up`**: el seed de [`db/init.sql`](db/init.sql) sólo corre en la **primera** creación del volumen de Postgres; si reusas datos viejos, haz `docker compose down -v` y vuelve a levantar. El usuario **`honeypot_readonly`** se crea en ese mismo init; volumen viejo puede no tenerlo hasta recrear volumen.
- **`docker logs honeypot-shipper` dice que espera `cowrie.json`**: Cowrie suele crear el archivo tras el primer contacto SSH al puerto **2222**; hasta entonces puede no haber ingestas nuevas desde el honeypot.
- **Puerto 2222 bloqueado** (Wi‑Fi institucional, firewall): hacer la parte “en vivo” desde la misma máquina con `ssh -p 2222 localhost` u ofrecer capturas/API como respaldo; revisa políticas antes de exponer honeypots.
- **Dashboard no cambia al instante**: Streamlit usa caché de ~5 segundos; refresca la página después de nuevos POST al API.

---

## Backlog opcional (no bloqueante de la demo)

- **Seguridad / producción**: el `POST /events` está pensado para la red Compose académica; una evolución mínima sería **Bearer token** sólo conocido por el shipper, **rate limiting** y política explícita de **retención** de datos. Las contraseñas capturadas son datos sensibles: no uses este despliegue en Internet abierto sin análisis de riesgos.
- **Análisis avanzado**: enriquecer con GeoIP por IP, etiquetado de familias de comandos y paneles tipo serie temporal; tratado como segunda iteración separada del flujo datos básicos.

---

## 📄 Documentación adicional

- [`docs/demo-checklist.md`](docs/demo-checklist.md) — Checklist antes de la presentación
- [`docs/tableplus.md`](docs/tableplus.md) — Conexión con TablePlus u otros GUI
- [`docs/quantas.md`](docs/quantas.md) — Architecture Quantas del sistema
- [`docs/adr/`](docs/adr/) — Architecture Decision Records (ADRs), incl. [ADR-005 shipper](docs/adr/ADR-005-shipper-ingesta-docker.md)
- [`docs/openapi.json`](docs/openapi.json) — Especificación OpenAPI de la API

---

## 🛑 Detener los servicios

```bash
docker compose down
```

Para eliminar también los volúmenes de datos (borra la base de datos):

```bash
docker compose down -v
```

---

## 👥 Equipo

Victor Benitez

Tamara Schnaas

Tania Hernández 

---

## 📚 Referencias

- [Cowrie Documentation](https://cowrie.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Architecture Decision Records (ADRs)](https://adr.github.io/)
