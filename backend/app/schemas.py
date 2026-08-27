from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    BuildingStatus,
    IncidentPriority,
    IncidentStatus,
    SensorType,
    UserRole,
)


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SetupStatus(BaseModel):
    needs_setup: bool


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MessageOut(BaseModel):
    message: str


# ---------- Plan ----------
class PlanUsage(BaseModel):
    used: int
    limit: int | None


class PlanStatusOut(BaseModel):
    plan: str
    polygons: PlanUsage
    buildings: PlanUsage
    users: PlanUsage


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: UserRole
    building_id: int | None
    created_at: datetime


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: UserRole = UserRole.viewer
    building_id: int | None = None


class UserUpdate(BaseModel):
    role: UserRole | None = None
    full_name: str | None = None
    building_id: int | None = None
    password: str | None = None


# ---------- Polygon ----------
class PolygonCreate(BaseModel):
    name: str
    address: str | None = None
    center_lat: float
    center_lng: float


class PolygonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    address: str | None
    center_lat: float
    center_lng: float
    created_at: datetime


# ---------- Building ----------
class BuildingCreate(BaseModel):
    name: str
    code: str
    building_type: str = "nave industrial"
    lat: float
    lng: float
    area_m2: float = 0


class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    polygon_id: int
    name: str
    code: str
    building_type: str
    lat: float
    lng: float
    area_m2: float
    status: BuildingStatus
    created_at: datetime
    temp_warning: float | None
    temp_critical: float | None
    vibration_warning: float | None
    vibration_critical: float | None
    humidity_warning: float | None
    humidity_critical: float | None
    energy_anomaly_warning_pct: float | None
    energy_anomaly_critical_pct: float | None


class BuildingWithPolygonOut(BuildingOut):
    polygon_name: str


class BuildingThresholdsUpdate(BaseModel):
    """Umbrales personalizados de una nave. Cualquier campo omitido o en
    `null` vuelve a usar (o mantiene) el valor global por defecto."""

    temp_warning: float | None = None
    temp_critical: float | None = None
    vibration_warning: float | None = None
    vibration_critical: float | None = None
    humidity_warning: float | None = None
    humidity_critical: float | None = None
    energy_anomaly_warning_pct: float | None = None
    energy_anomaly_critical_pct: float | None = None


# ---------- Sensor ----------
class SensorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    building_id: int
    sensor_type: SensorType
    name: str
    unit: str
    is_simulated: bool


class SensorLatest(SensorOut):
    latest_value: float | None
    latest_timestamp: datetime | None


class SensorApiKeyOut(BaseModel):
    """Solo para admins: la clave que hay que programar en el dispositivo
    fisico (ESP32...) para que pueda mandar lecturas de este sensor."""

    sensor_id: int
    api_key: str


class SensorReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    value: float
    timestamp: datetime


# ---------- Alert ----------
class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    building_id: int
    sensor_id: int | None
    severity: AlertSeverity
    alert_type: AlertType
    message: str
    value: float | None
    threshold: float | None
    status: AlertStatus
    created_at: datetime
    resolved_at: datetime | None


# ---------- Incident ----------
class IncidentCreate(BaseModel):
    title: str
    description: str | None = None
    priority: IncidentPriority = IncidentPriority.medium


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    priority: IncidentPriority | None = None


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    building_id: int
    title: str
    description: str | None
    priority: IncidentPriority
    status: IncidentStatus
    created_at: datetime
    resolved_at: datetime | None


# ---------- Ingest (para ESP32 / simulador) ----------
class ReadingIngest(BaseModel):
    sensor_id: int
    api_key: str
    value: float
    timestamp: datetime | None = None


# ---------- Dashboards agregados ----------
class SeriesPoint(BaseModel):
    timestamp: datetime
    value: float


class BuildingRankingItem(BaseModel):
    building_id: int
    name: str
    total_energy_kwh: float
    efficiency_kwh_per_m2: float | None
    efficiency_score: int


class PolygonDashboardOut(BaseModel):
    polygon: PolygonOut
    building_count: int
    total_energy_kwh_24h: float
    energy_trend_pct: float | None
    predicted_energy_kwh_24h: float | None
    active_alerts_count: int
    overall_status: BuildingStatus
    energy_series: list[SeriesPoint]
    temperature_series: list[SeriesPoint]
    predicted_energy_series: list[SeriesPoint]
    ranking: list[BuildingRankingItem]
    recent_alerts: list[AlertOut]


class BuildingDashboardOut(BaseModel):
    building: BuildingOut
    sensors: list[SensorLatest]
    active_alerts: list[AlertOut]
    incidents: list[IncidentOut]
    efficiency_kwh_per_m2: float | None
    efficiency_score: int
    polygon_avg_kwh_per_m2: float | None
    predicted_energy_kwh_24h: float | None
    maintenance_risk_score: int
    maintenance_risk_label: str
