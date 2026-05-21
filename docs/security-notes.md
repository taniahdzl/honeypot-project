# Notas de seguridad de la demo

## Token entre shipper y API

`POST /events` está protegido con un Bearer token simple para evitar inserciones accidentales o triviales desde clientes no autorizados durante la demo local.

La API y el shipper deben compartir la misma variable:

```env
SHIPPER_TOKEN=demo-secret-token
```

Docker Compose pasa esta variable a los servicios `api` y `shipper`. Si no se define, ambos usan `demo-secret-token` como valor por defecto para que la demo académica local siga funcionando después de copiar `.env.example`.

## Probar con curl

Sin token, debe fallar:

```bash
curl -i -X POST http://127.0.0.1:8000/events \
  -H "Content-Type: application/json" \
  -d '{"src_ip":"203.0.113.44","event_type":"cowrie.login.failed"}'
```

Con token incorrecto, debe fallar:

```bash
curl -i -X POST http://127.0.0.1:8000/events \
  -H "Authorization: Bearer token-incorrecto" \
  -H "Content-Type: application/json" \
  -d '{"src_ip":"203.0.113.44","event_type":"cowrie.login.failed"}'
```

Con token correcto, debe insertar:

```bash
curl -i -X POST http://127.0.0.1:8000/events \
  -H "Authorization: Bearer ${SHIPPER_TOKEN:-demo-secret-token}" \
  -H "Content-Type: application/json" \
  -d '{"src_ip":"203.0.113.44","event_type":"cowrie.login.failed","username":"root","password":"password"}'
```

## Alcance

Esta protección es suficiente para una demo local defendible. No reemplaza autenticación robusta, gestión de secretos, TLS, rate limiting ni controles de retención necesarios en un despliegue real.
