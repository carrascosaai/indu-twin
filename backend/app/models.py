import enum
import secrets
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def generate_sensor_api_key() -> str:
    return secrets.token_urlsafe(24)


class BuildingStatus(enum.StrEnum):
    normal = "normal"
    warning = "warning"
    critical = "critical"


class SensorType(enum.StrEnum):
    temperature = "temperature"
    energy = "energy"
    vibration = "vibration"
    humidity = "humidity"


# Sensores que se aprovisionan automaticamente en cada nave nueva, en
# seed.py y al crear una nave desde la API. Unica fuente de verdad para
# que ambos caminos generen exactamente el mismo set de sensores.
DEFAULT_SENSOR_TEMPLATES: list[tuple[SensorType, str, str]] = [
    (SensorType.temperature, "Temperatura interior", "C"),
    (SensorType.energy, "Consumo electrico", "kWh"),
    (SensorType.vibration, "Vibracion maquinaria", "mm/s"),
    (SensorType.humidity, "Humedad relativa", "%"),
]


class AlertSeverity(enum.StrEnum):
    warning = "warning"
    critical = "critical"


class AlertType(enum.StrEnum):
    threshold = "threshold"
    anomaly = "anomaly"


class AlertStatus(enum.StrEnum):
    active = "active"
    resolved = "resolved"


class IncidentPriority(enum.StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class IncidentStatus(enum.StrEnum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class UserRole(enum.StrEnum):
    admin = "admin"
    viewer = "viewer"
    # Empresa individual dentro de un poligono: solo ve su propia nave, nunca
    # el resto del poligono ni otras empresas vecinas. Pensado para que el
    # gestor del poligono pueda dar acceso de autoservicio a sus inquilinos
    # sin exponer datos ajenos.
    tenant = "tenant"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.viewer)
    # Solo se usa (y es obligatorio) cuando role == tenant.
    building_id: Mapped[int | None] = mapped_column(ForeignKey("buildings.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Recuperacion de contrasena: hash del token vigente (None si no hay
    # ninguna solicitud pendiente) y su caducidad. Pedir uno nuevo invalida
    # el anterior al sobrescribir estos campos.
    reset_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Chat de Telegram donde este usuario quiere recibir alertas criticas
    # (ademas del email, si esta configurado). Lo rellena el propio usuario
    # (no un admin por el): tiene que haber hablado con el bot primero para
    # conseguir su chat_id. None = no quiere/no ha configurado Telegram.
    telegram_chat_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    building: Mapped["Building | None"] = relationship()


class Polygon(Base):
    __tablename__ = "polygons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    center_lat: Mapped[float] = mapped_column(Float, nullable=False)
    center_lng: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    buildings: Mapped[list["Building"]] = relationship(
        back_populates="polygon", cascade="all, delete-orphan"
    )


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    polygon_id: Mapped[int] = mapped_column(ForeignKey("polygons.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    building_type: Mapped[str] = mapped_column(String(60), default="nave industrial")
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    area_m2: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[BuildingStatus] = mapped_column(
        Enum(BuildingStatus), default=BuildingStatus.normal
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Umbrales personalizados por nave. NULL = usa el valor global por
    # defecto (ver app/services/anomaly_rules.py). Permiten que, por
    # ejemplo, un taller con hornos tenga un umbral de temperatura mas
    # alto que una oficina sin que salte una alerta constantemente.
    temp_warning: Mapped[float | None] = mapped_column(Float, nullable=True)
    temp_critical: Mapped[float | None] = mapped_column(Float, nullable=True)
    vibration_warning: Mapped[float | None] = mapped_column(Float, nullable=True)
    vibration_critical: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_warning: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_critical: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_anomaly_warning_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_anomaly_critical_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    polygon: Mapped["Polygon"] = relationship(back_populates="buildings")
    sensors: Mapped[list["Sensor"]] = relationship(
        back_populates="building", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="building", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(
        back_populates="building", cascade="all, delete-orphan"
    )


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    sensor_type: Mapped[SensorType] = mapped_column(Enum(SensorType), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    # Clave que debe mandar un dispositivo real (ESP32...) al ingestar una
    # lectura via /api/ingest/reading. Sin ella, cualquiera podria inyectar
    # lecturas falsas en cualquier sensor de cualquier cliente.
    api_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=generate_sensor_api_key
    )
    # True mientras nadie ha mandado una lectura real via /api/ingest/reading
    # con la api_key de este sensor: el simulador sigue generando datos de
    # mentira para el. En cuanto llega la primera lectura real (ver
    # app/routers/ingest.py), se pone a False y el simulador deja de tocarlo
    # — si no, el dispositivo real y el simulador mezclarian datos falsos y
    # reales en el mismo sensor.
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    building: Mapped["Building"] = relationship(back_populates="sensors")
    readings: Mapped[list["SensorReading"]] = relationship(
        back_populates="sensor", cascade="all, delete-orphan"
    )


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_id: Mapped[int] = mapped_column(
        ForeignKey("sensors.id"), nullable=False, index=True
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    sensor: Mapped["Sensor"] = relationship(back_populates="readings")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    sensor_id: Mapped[int | None] = mapped_column(ForeignKey("sensors.id"), nullable=True)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    building: Mapped["Building"] = relationship(back_populates="alerts")


class ReportSchedule(Base):
    """Estado de los informes automaticos por email, por poligono y periodo
    (weekly/monthly). Se guarda en la base de datos (no en memoria ni en
    disco) para que sobreviva a que el proceso se reinicie o el servicio se
    duerma por inactividad (plan free de Render) - sin esto, cada reinicio
    olvidaria cuando toca mandar el siguiente informe."""

    __tablename__ = "report_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    polygon_id: Mapped[int] = mapped_column(ForeignKey("polygons.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)  # "weekly" | "monthly"
    last_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    polygon: Mapped["Polygon"] = relationship()


class EnergyGoal(Base):
    """Objetivo de reduccion de consumo configurable por un admin, con una
    linea base capturada al crearlo para poder calcular el progreso real
    sin depender de que nadie vuelva a introducir datos manualmente."""

    __tablename__ = "energy_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    polygon_id: Mapped[int] = mapped_column(ForeignKey("polygons.id"), nullable=False)
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id"), nullable=True
    )  # None = objetivo para todo el poligono
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    target_reduction_pct: Mapped[float] = mapped_column(Float, nullable=False)
    # kWh consumidos en los `baseline_days` anteriores a la creacion del
    # objetivo - el punto de comparacion fijo contra el que se mide el
    # progreso, para que no se mueva la meta mientras el objetivo esta activo.
    baseline_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_days: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    polygon: Mapped["Polygon"] = relationship()
    building: Mapped["Building | None"] = relationship()


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[IncidentPriority] = mapped_column(
        Enum(IncidentPriority), default=IncidentPriority.medium
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus), default=IncidentStatus.open
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    building: Mapped["Building"] = relationship(back_populates="incidents")
