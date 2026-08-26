# INDU-TWIN — MVP

Digital Twin para pequeños polígonos industriales. Backend con datos simulados realistas, reglas de anomalías, autenticación con roles y multi-polígono; frontend con mapa, dashboard, panel de nave y vista global de alertas/incidencias.

## Estructura

```
backend/    FastAPI + SQLAlchemy + SQLite, simulador y reglas de anomalías
frontend/   React + Vite + TypeScript + Tailwind + Leaflet + Recharts
```

## Backend

```bash
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python seed.py        # crea el polígono demo + histórico de 7 días (solo la primera vez)
venv\Scripts\uvicorn app.main:app --port 8010
```

- API en `http://127.0.0.1:8010`, docs interactivas en `http://127.0.0.1:8010/docs`.
- El simulador genera lecturas nuevas cada 15s (`SIMULATION_INTERVAL_SECONDS` en `.env`) y evalúa las reglas de anomalías automáticamente.
- Base de datos SQLite en `backend/indu_twin.db`. Para Postgres, cambia `DATABASE_URL` en `.env`.
- **Copias de seguridad automáticas**: al arrancar y cada 24h se copia la base de datos a `backend/backups/` (se conservan las últimas 14). Para restaurar: para el backend, sustituye `indu_twin.db` por la copia elegida, arranca de nuevo.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

- App en `http://localhost:5173`.
- Configura la URL del backend en `frontend/.env` (`VITE_API_URL`, ver `.env.example`).
- `npm run build` compila y type-checka para producción; `npx tsc -b` solo type-checka.

## Docker

```bash
docker compose up --build
```

- Backend en `http://localhost:8010`, frontend (servido por nginx) en `http://localhost:8080`.
- La primera vez que arranca el contenedor del backend sin base de datos existente, genera automáticamente los datos de demo (`docker-entrypoint.sh` ejecuta `seed.py`).
- Los datos persisten en el volumen `indu_twin_data` entre reinicios; para partir de cero: `docker compose down -v`. Las copias de seguridad automáticas (ver más abajo) se guardan dentro del mismo volumen, en `/app/data/backups`.
- En producción real, define `JWT_SECRET_KEY` (variable de entorno o `.env` junto a `docker-compose.yml`) en vez de usar el valor de desarrollo por defecto.
- El plan comercial de esta instancia se fija con `PLAN=free|pro|business` (por defecto `free`). Cada cliente tiene su propio despliegue, así que el plan es una propiedad de la instancia, no de una organización dentro de una base de datos compartida.

## Despliegue gratis (Vercel + Render)

Ver [`DEPLOY.md`](DEPLOY.md) para el paso a paso: frontend en Vercel, backend en Render, usando [`render.yaml`](render.yaml) como blueprint.

## CI

`.github/workflows/ci.yml` corre en cada push/PR a `main`/`master`: lint (`ruff`) + tests (`pytest`) del backend, y type-check + build del frontend.

## Funcionalidades

- Dashboard por polígono: mapa (Leaflet) o **vista 3D** intercambiable, KPIs con tendencia vs. periodo anterior, evolución de consumo real y previsto, ranking de naves con indicador de eficiencia.
- Panel de nave: sensores en vivo, históricos con rango 24h/7d/30d, alertas, incidencias, eficiencia comparada con la media del polígono, riesgo de mantenimiento.
- Vista global de alertas e incidencias por polígono (`/polygon/:id/alerts`), con filtros por estado.
- Exportación CSV de alertas y lecturas.
- **Informes periódicos en PDF y Excel** (botón "Informes" en el dashboard del polígono): diario, semanal o mensual, con KPIs del periodo (consumo, tendencia vs. periodo anterior, temperatura media, alertas, incidencias), tabla de consumo/eficiencia/riesgo por nave y detalle de las alertas más recientes. `GET /api/polygons/{id}/reports/{daily|weekly|monthly}?format=pdf|xlsx` (`app/services/reports.py`).
- Autenticación JWT con roles **admin / viewer / tenant** (empresa individual dentro de un polígono, ve solo su propia nave — pensado para que el gestor del polígono dé acceso de autoservicio a sus inquilinos sin exponer datos de otras empresas), multi-polígono.
- **Alta de la primera cuenta**: cada cliente tiene su propio despliegue (ver Docker más abajo); la primera vez que arranca sin usuarios, `/login` ofrece crear la cuenta admin inicial sin tocar la base de datos a mano.
- **Notificaciones por email** de alertas críticas nuevas (o que escalan a crítico) a los administradores/operarios y a la empresa dueña de la nave si tiene cuenta tenant. Desactivado por defecto; se activa configurando `SMTP_*` en `.env` (ver `.env.example`).
- **Recuperación de contraseña** (`/login` → "¿Olvidaste tu contraseña?"): enlace de un solo uso válido 1h. Sin `SMTP_*` configurado, el enlace se deja en el log del backend para poder probarlo en desarrollo.
- **Ingesta de sensores protegida por API key**: cada sensor tiene su propia clave (visible/regenerable por un admin desde el icono de llave en el panel de nave) que un dispositivo físico debe mandar en `/api/ingest/reading` — sin ella no se pueden inyectar lecturas falsas.
- **Límites por plan** (FREE 1 polígono/3 naves/2 usuarios, PRO 3/15/10, BUSINESS sin límite): se aplican al crear polígonos/naves/usuarios y se ven en el pie del menú lateral y en `GET /api/plan`.
- Detección de anomalías por reglas (umbrales + desviación sobre la media histórica), con **umbrales configurables por nave** (admin, botón "Umbrales de alerta" en el panel de nave) que sobrescriben los globales por defecto — útil para naves con procesos especiales (hornos, cámaras frigoríficas...).
- Indicadores de eficiencia energética (kWh/m²) por nave, puntuados 0-100 frente al resto del polígono.
- **Predicción de consumo**: perfil horario promedio de los últimos 7 días, proyectado a las próximas 24h (`app/services/prediction.py`).
- **Mantenimiento predictivo**: puntuación de riesgo 0-100 por nave, combinando frecuencia de alertas y tendencia de vibración (`app/services/maintenance.py`).
- **Vista 3D** del polígono (Three.js / react-three-fiber): cada nave como volumen coloreado por estado, cargada bajo demanda para no penalizar el bundle principal.

## Diseño

Interfaz con iconos [lucide-react](https://lucide.dev), estados de carga tipo *skeleton*, badges de eficiencia y tendencia con color semántico, y estados vacíos/error explícitos en toda la app (nunca se queda cargando indefinidamente si el backend no responde).

## Autenticación

La API exige JWT en todos los endpoints salvo `/api/auth/login`, `/api/auth/register` (solo funciona sin usuarios todavía), `/api/health` y `/api/ingest/reading` (este último lo llaman dispositivos, no el navegador — se autentica con la API key propia de cada sensor, no con JWT). Cuentas demo creadas por `seed.py`:

| Email | Contraseña | Rol |
|---|---|---|
| admin@indutwin.com | admin123 | admin (puede crear polígonos/naves) |
| viewer@indutwin.com | viewer123 | viewer (puede resolver alertas y gestionar incidencias) |
| empresa@indutwin.com | empresa123 | tenant (solo ve la nave A1) |

## Tests

```bash
cd backend
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\pytest -v
```

138 tests: reglas de anomalías y umbrales por nave (unitarios), autenticación/roles/rate limiting, tenant scoping, límites por plan, recuperación de contraseña, API keys de sensor, informes PDF/Excel, CRUD de polígonos/naves/usuarios, alertas e incidencias (integración contra una base de datos SQLite en memoria, aislada de `indu_twin.db`).

## Calidad de código

```bash
cd backend
venv\Scripts\ruff check app seed.py tests
```

```bash
cd frontend
npx tsc -b        # type-check
npm run build     # build de producción
```

## Notas

- Puertos 8000 y 8001 están ocupados por otras apps tuyas en esta máquina (una de ellas, OLEAMIND AI, reclama el 8001 en cuanto queda libre) — INDU-TWIN usa el 8010 para evitar choques.
- Endpoint `/api/ingest/reading` ya preparado para que un ESP32 real envíe lecturas por HTTP (misma lógica de reglas/alertas que el simulador).
- Hay 2 polígonos demo (El Prado y Malpica) para probar el selector multi-polígono del sidebar.
- Si cambias el modelo de datos, borra `backend/indu_twin.db` y vuelve a correr `seed.py` (SQLite no migra automáticamente).
