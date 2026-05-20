.PHONY: up down clean demo-smoke demo-traffic logs ps help

## Levanta todos los servicios en background
up:
	docker compose up --build -d

## Detiene todos los servicios
down:
	docker compose down

## Detiene servicios y elimina volúmenes (borra la BD y reinicia seed)
clean:
	docker compose down -v

## Humo rápido contra la API local (requiere servicios arriba)
demo-smoke:
	@chmod +x scripts/demo-smoke.sh
	API_BASE_URL=http://127.0.0.1:$${API_PORT:-8000} ./scripts/demo-smoke.sh

## Genera eventos demo constantes durante ~10 minutos
demo-traffic:
	@chmod +x scripts/demo-traffic.sh
	API_BASE_URL=http://127.0.0.1:$${API_PORT:-8000} ./scripts/demo-traffic.sh

## Muestra el estado de los contenedores
ps:
	docker compose ps

## Muestra logs de todos los servicios (Ctrl+C para salir)
logs:
	docker compose logs -f

## Muestra logs de un servicio específico: make logs-api | logs-dashboard | logs-shipper | logs-db | logs-cowrie
logs-api:
	docker compose logs -f api

logs-dashboard:
	docker compose logs -f dashboard

logs-shipper:
	docker compose logs -f shipper

logs-db:
	docker compose logs -f db

logs-cowrie:
	docker compose logs -f cowrie

## Ayuda — lista todos los targets disponibles
help:
	@echo ""
	@echo "Targets disponibles:"
	@echo "  make up            — Construye y levanta los 5 servicios"
	@echo "  make down          — Detiene los servicios"
	@echo "  make clean         — Detiene y elimina volúmenes (reinicia BD)"
	@echo "  make demo-smoke    — Humo HTTP contra /health, /events, /stats"
	@echo "  make demo-traffic  — Genera eventos visibles en dashboard (~10 min)"
	@echo "  make ps            — Estado de los contenedores"
	@echo "  make logs          — Logs de todos los servicios"
	@echo "  make logs-api      — Logs solo de FastAPI"
	@echo "  make logs-shipper  — Logs solo del shipper"
	@echo "  make logs-cowrie   — Logs solo de Cowrie"
	@echo ""
