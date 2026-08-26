import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.deps import get_db
from app.main import app
from app.models import Building, Polygon, Sensor, SensorType, User, UserRole
from app.security import hash_password
from app.services import rate_limit

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def _fresh_database(monkeypatch):
    Base.metadata.create_all(bind=engine)
    rate_limit._attempts.clear()
    # Los tests no deben depender del .env local del desarrollador (p.ej. un
    # PLAN=business puesto para la demo): se fija el plan por defecto salvo
    # que un test concreto lo sobreescriba explicitamente.
    monkeypatch.setattr(settings, "plan", "free")
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_user(db_session):
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("admin123"),
        full_name="Test Admin",
        role=UserRole.admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def viewer_user(db_session):
    user = User(
        email="viewer@test.com",
        hashed_password=hash_password("viewer123"),
        full_name="Test Viewer",
        role=UserRole.viewer,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(client, admin_user):
    resp = client.post(
        "/api/auth/login", json={"email": "admin@test.com", "password": "admin123"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(client, viewer_user):
    resp = client.post(
        "/api/auth/login", json={"email": "viewer@test.com", "password": "viewer123"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tenant_user(db_session, building):
    user = User(
        email="tenant@test.com",
        hashed_password=hash_password("tenant123"),
        full_name="Test Tenant",
        role=UserRole.tenant,
        building_id=building.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def tenant_headers(client, tenant_user):
    resp = client.post(
        "/api/auth/login", json={"email": "tenant@test.com", "password": "tenant123"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def polygon(db_session):
    p = Polygon(name="Test Polygon", address="Test City", center_lat=41.0, center_lng=-1.0)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def building(db_session, polygon):
    b = Building(
        polygon_id=polygon.id,
        name="Test Building",
        code="T1",
        building_type="taller",
        lat=41.0,
        lng=-1.0,
        area_m2=1000,
    )
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)
    return b


@pytest.fixture
def other_building(db_session, polygon):
    b = Building(
        polygon_id=polygon.id,
        name="Other Building",
        code="T2",
        building_type="almacen",
        lat=41.1,
        lng=-1.1,
        area_m2=800,
    )
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)
    return b


@pytest.fixture
def temperature_sensor(db_session, building):
    s = Sensor(building_id=building.id, sensor_type=SensorType.temperature, name="Temp", unit="C")
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def energy_sensor(db_session, building):
    s = Sensor(building_id=building.id, sensor_type=SensorType.energy, name="Energy", unit="kWh")
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s
