import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import (
    alerts,
    auth,
    buildings,
    dashboard,
    export,
    goals,
    incidents,
    ingest,
    plan,
    polygons,
    reports,
    sensors,
    users,
)
from app.services.backup import backup_loop
from app.services.mqtt_ingest import start_mqtt_client
from app.services.scheduled_reports import scheduled_reports_loop
from app.services.simulator import simulation_loop

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(simulation_loop())
    backup_task = asyncio.create_task(backup_loop())
    reports_task = asyncio.create_task(scheduled_reports_loop())
    mqtt_client = start_mqtt_client()
    yield
    task.cancel()
    backup_task.cancel()
    reports_task.cancel()
    if mqtt_client:
        mqtt_client.loop_stop()


app = FastAPI(title="INDU-TWIN API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(polygons.router)
app.include_router(buildings.router)
app.include_router(sensors.router)
app.include_router(alerts.router)
app.include_router(incidents.router)
app.include_router(dashboard.router)
app.include_router(export.router)
app.include_router(ingest.router)
app.include_router(users.router)
app.include_router(plan.router)
app.include_router(reports.router)
app.include_router(goals.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
