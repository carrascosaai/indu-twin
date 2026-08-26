"""Crea datos demo: usuarios, 2 poligonos con naves y sensores, e historico de 7 dias.

Uso:
    python seed.py
"""

from app.database import Base, SessionLocal, engine
from app.models import DEFAULT_SENSOR_TEMPLATES, Building, Polygon, Sensor, User, UserRole
from app.security import hash_password
from app.services.simulator import backfill_history

USERS = [
    {
        "email": "admin@indutwin.com",
        "password": "admin123",
        "full_name": "Administrador INDU-TWIN",
        "role": UserRole.admin,
    },
    {
        "email": "viewer@indutwin.com",
        "password": "viewer123",
        "full_name": "Operario de planta",
        "role": UserRole.viewer,
    },
]

# Cuenta de empresa (tenant): se asigna a la primera nave del primer
# poligono una vez creadas las naves (ver mas abajo). Solo ve su propia nave.
TENANT_USER = {
    "email": "empresa@indutwin.com",
    "password": "empresa123",
    "full_name": "Logística Norte S.L.",
    "role": UserRole.tenant,
}

POLYGONS = [
    {
        "polygon": {
            "name": "Polígono Industrial El Prado",
            "address": "Zaragoza, España",
            "center_lat": 41.6296,
            "center_lng": -0.8600,
        },
        "buildings": [
            {"name": "Nave A1 - Logística Norte", "code": "A1", "building_type": "logística", "lat": 41.6310, "lng": -0.8625, "area_m2": 3200},
            {"name": "Nave A2 - Metalúrgica", "code": "A2", "building_type": "producción", "lat": 41.6305, "lng": -0.8610, "area_m2": 4500},
            {"name": "Nave B1 - Almacén General", "code": "B1", "building_type": "almacén", "lat": 41.6292, "lng": -0.8595, "area_m2": 2800},
            {"name": "Nave B2 - Envasado", "code": "B2", "building_type": "producción", "lat": 41.6288, "lng": -0.8580, "area_m2": 3900},
            {"name": "Nave C1 - Taller Mecánico", "code": "C1", "building_type": "taller", "lat": 41.6280, "lng": -0.8615, "area_m2": 2100},
            {"name": "Nave C2 - Centro Logístico Sur", "code": "C2", "building_type": "logística", "lat": 41.6275, "lng": -0.8590, "area_m2": 5200},
        ],
    },
    {
        "polygon": {
            "name": "Polígono Industrial Malpica",
            "address": "Zaragoza, España",
            "center_lat": 41.6690,
            "center_lng": -0.8330,
        },
        "buildings": [
            {"name": "Nave D1 - Componentes Auto", "code": "D1", "building_type": "producción", "lat": 41.6700, "lng": -0.8345, "area_m2": 3600},
            {"name": "Nave D2 - Centro de Distribución", "code": "D2", "building_type": "logística", "lat": 41.6685, "lng": -0.8320, "area_m2": 6100},
            {"name": "Nave D3 - Carpintería Industrial", "code": "D3", "building_type": "taller", "lat": 41.6678, "lng": -0.8338, "area_m2": 1900},
        ],
    },
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Polygon).first():
            print("Ya existen datos. No se vuelve a sembrar.")
            return

        for u in USERS:
            db.add(
                User(
                    email=u["email"],
                    hashed_password=hash_password(u["password"]),
                    full_name=u["full_name"],
                    role=u["role"],
                )
            )
        db.commit()
        print("Usuarios demo creados:")
        for u in USERS:
            print(f"  - {u['email']} / {u['password']} ({u['role'].value})")

        first_building_id: int | None = None
        for entry in POLYGONS:
            polygon = Polygon(**entry["polygon"])
            db.add(polygon)
            db.flush()

            for b in entry["buildings"]:
                building = Building(polygon_id=polygon.id, **b)
                db.add(building)
                db.flush()
                if first_building_id is None:
                    first_building_id = building.id
                for sensor_type, name, unit in DEFAULT_SENSOR_TEMPLATES:
                    db.add(
                        Sensor(
                            building_id=building.id,
                            sensor_type=sensor_type,
                            name=name,
                            unit=unit,
                        )
                    )
            db.commit()
            print(f"Poligono '{polygon.name}' creado con {len(entry['buildings'])} naves.")

        db.add(
            User(
                email=TENANT_USER["email"],
                hashed_password=hash_password(TENANT_USER["password"]),
                full_name=TENANT_USER["full_name"],
                role=TENANT_USER["role"],
                building_id=first_building_id,
            )
        )
        db.commit()
        print(
            f"  - {TENANT_USER['email']} / {TENANT_USER['password']} "
            f"(tenant, solo ve la nave {first_building_id})"
        )

        print("Generando historico de 7 dias (puede tardar unos segundos)...")
        backfill_history(db, days=7, step_minutes=60)
        print("Historico generado.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
