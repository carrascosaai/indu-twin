"""Ingesta de sensores ESP32 reales via MQTT.

Desactivado por defecto (MQTT_ENABLED=false) porque en desarrollo no hay
broker disponible. El dia que haya hardware real, basta con:
  1. Levantar un broker (ej. Mosquitto).
  2. Poner MQTT_ENABLED=true y MQTT_BROKER_HOST en el .env.
  3. Programar el ESP32 para publicar en el topic `indu-twin/sensors/{sensor_id}/reading`
     con un payload JSON: {"value": 23.4}

Reutiliza `process_new_reading`, la misma funcion que usa el simulador y el
endpoint HTTP /api/ingest/reading, para que las reglas de anomalias se
apliquen igual sin importar el origen del dato.
"""

import json
import logging

from app.config import settings
from app.database import SessionLocal
from app.models import Sensor
from app.services.simulator import process_new_reading

logger = logging.getLogger("indu_twin.mqtt")

TOPIC_PATTERN = "indu-twin/sensors/+/reading"


def _on_connect(client, userdata, flags, reason_code, properties=None):
    logger.info("Conectado al broker MQTT (rc=%s)", reason_code)
    client.subscribe(TOPIC_PATTERN)


def _on_message(client, userdata, msg):
    try:
        sensor_id = int(msg.topic.split("/")[2])
        payload = json.loads(msg.payload.decode("utf-8"))
        value = float(payload["value"])
    except (IndexError, ValueError, KeyError, json.JSONDecodeError):
        logger.warning("Mensaje MQTT invalido en topic %s: %r", msg.topic, msg.payload)
        return

    db = SessionLocal()
    try:
        sensor = db.get(Sensor, sensor_id)
        if not sensor:
            logger.warning("Sensor %s no existe, se ignora la lectura MQTT", sensor_id)
            return
        process_new_reading(db, sensor, value)
        db.commit()
    finally:
        db.close()


def start_mqtt_client():
    """Arranca el cliente MQTT en un hilo propio. Devuelve None si esta desactivado."""
    if not settings.mqtt_enabled:
        logger.info("Ingesta MQTT desactivada (MQTT_ENABLED=false)")
        return None

    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        logger.error("paho-mqtt no esta instalado; ejecuta `pip install paho-mqtt`")
        return None

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, keepalive=60)
    client.loop_start()
    logger.info(
        "Cliente MQTT iniciado hacia %s:%s", settings.mqtt_broker_host, settings.mqtt_broker_port
    )
    return client
