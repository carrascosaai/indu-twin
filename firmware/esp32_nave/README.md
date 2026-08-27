# Firmware ESP32 — una nave de INDU-TWIN

Lee temperatura, humedad, vibración y consumo eléctrico y los manda al
backend real (`https://indu-twin-backend.onrender.com/api/ingest/reading`),
el mismo endpoint que ya usa el simulador — la app no distingue un dato
simulado de uno real.

**Aviso**: este código se ha escrito sin una placa delante — no se ha podido
compilar ni probar en hardware real. Sigue la sección "Probar antes de
confiar en ello" antes de dejarlo funcionando solo.

## Hardware

| Componente | Conexión al ESP32 |
|---|---|
| DHT22 (temp/humedad) | VCC→3V3, GND→GND, DATA→GPIO4 (con resistencia pull-up de 10kΩ entre DATA y VCC si el módulo no la trae ya integrada) |
| ADXL345 (vibración) | VCC→3V3, GND→GND, SDA→GPIO21, SCL→GPIO22 (pines I2C por defecto del ESP32) |
| PZEM-004T v3.0 (consumo) | 5V→5V, GND→GND, TX→GPIO16 (RX2), RX→GPIO17 (TX2) — **y el clamp de corriente alrededor del cable de fase de la nave, instalado por alguien con conocimientos eléctricos** |

Todos los sensores comparten alimentación 3.3V/5V y masa con el ESP32;
solo cambian los pines de datos.

## Librerías a instalar (Arduino IDE → Gestor de Librerías)

- **DHT sensor library** (Adafruit)
- **Adafruit Unified Sensor** (dependencia de la anterior)
- **PZEM004Tv30** (Jakub Mandula)

El ADXL345 se lee por I2C directo con `Wire.h`, que ya viene con el core
de ESP32 — no hace falta instalar nada extra para ese sensor.

## Configurar el sketch

Antes de subirlo, edita estas líneas en `esp32_nave.ino`:

```cpp
const char* WIFI_SSID = "TU_WIFI";
const char* WIFI_PASSWORD = "TU_CONTRASEÑA_WIFI";

SensorConfig SENSOR_TEMPERATURA = {0, "PON_AQUI_LA_API_KEY"};
SensorConfig SENSOR_HUMEDAD     = {0, "PON_AQUI_LA_API_KEY"};
SensorConfig SENSOR_VIBRACION   = {0, "PON_AQUI_LA_API_KEY"};
SensorConfig SENSOR_CONSUMO     = {0, "PON_AQUI_LA_API_KEY"};
```

### Cómo conseguir el `sensor_id` y la `api_key` de cada sensor

1. Entra en INDU-TWIN como admin → abre la nave donde vas a instalar el
   hardware.
2. En cada tarjeta de sensor (Temperatura, Humedad, Vibración, Consumo
   eléctrico) hay un icono de llave 🔑 — púlsalo para ver la clave de ese
   sensor concreto.
3. El `sensor_id` no se muestra en la interfaz todavía; sácalo así, con tu
   token de admin (Ajustes del navegador → pestaña Red, tras iniciar
   sesión, copia el header `Authorization` de cualquier petición):

   ```bash
   curl https://indu-twin-backend.onrender.com/api/buildings/<ID_DE_LA_NAVE>/sensors \
     -H "Authorization: Bearer <TU_TOKEN>"
   ```

   Esto devuelve los 4 sensores de esa nave con su `id` y `sensor_type`
   (`temperature`, `humidity`, `vibration`, `energy`) — empareja cada uno
   con la clave que copiaste en el paso 2.

## Probar antes de confiar en ello

No subas el sketch completo a ciegas. Antes de montarlo en la nave:

1. **Prueba cada sensor por separado** con el monitor serie abierto
   (115200 baudios) y valores de ejemplo razonables — confirma que
   `dht.readTemperature()`, la lectura del ADXL345 y `pzem.energy()`
   imprimen números con sentido antes de conectarlos a INDU-TWIN.
2. **Prueba el envío HTTP con un solo sensor primero** — sube el sketch con
   solo `SENSOR_TEMPERATURA` configurado (deja los otros tres en
   `sensorId = 0`, así `sendReading` los omite automáticamente) y confirma
   en el panel de la nave que la lectura llega y se ve razonable.
3. **Calibra el factor de vibración**: el número que manda el ADXL345 es
   una aproximación (`SCALE_TO_APPROX_MMS` en el código), no una medida
   industrial calibrada de mm/s. Con la máquina parada debería dar un valor
   bajo y estable; en marcha, más alto. Ajusta el factor de escala
   observando esos dos casos reales, no lo des por bueno tal cual.
4. Solo cuando los cuatro funcionen por separado, deja el sketch completo
   corriendo solo.

## Ajustar la frecuencia de envío

`SEND_INTERVAL_MS` está puesto a 60 segundos — razonable para una nave real
(no hace falta la frecuencia de 15s del simulador, que solo existe para que
la demo se vea "viva"). Súbelo a 5 minutos o más si quieres ahorrar datos/
batería en un despliegue con muchos dispositivos.
