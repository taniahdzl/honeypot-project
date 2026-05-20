# Dashboard Streamlit

El dashboard consume la API pública de lectura (`/health`, `/events`, `/stats`) y se refresca automáticamente cada 5 segundos.

## Filtros

La barra lateral permite filtrar la tabla y las gráficas por:

- Rango de fechas, cuando existe `event_time`.
- Tipo de evento (`event_type`).
- IP origen (`src_ip`).
- Usuario (`username`).

Si un campo no existe o viene vacío, el dashboard lo omite sin detener la aplicación.

## Visualizaciones

La vista incluye:

- Estado del sistema: API, PostgreSQL y conteo de eventos.
- Último evento recibido.
- Tabla de eventos recientes.
- Serie temporal `Eventos por hora`.
- Top IPs.
- Tipos de evento.

## Contraseñas

Por defecto las contraseñas se muestran enmascaradas. La opción `Mostrar contraseñas` permite verlas en claro durante una explicación controlada, pero debe mantenerse desactivada para la presentación normal.
