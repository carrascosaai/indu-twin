# Firmware ESP32 — una nave de INDU-TWIN

Lee temperatura, vibración y consumo eléctrico y los manda al backend real
(`https://indu-twin-backend.onrender.com/api/ingest/reading`), el mismo
endpoint que ya usa el simulador — la app no distingue un dato simulado de
uno real.

**Este sketch está escrito para el kit de hardware concreto que se compró**
(DS18B20 + ADXL345 + SCT-013-000), no para sensores genéricos. Si compras
otra cosa, el código de lectura de ese sensor hay que adaptarlo.

**No hay sensor de humedad en este kit.** La tarjeta de humedad de la app se
queda mostrando datos del simulador de forma permanente (con la etiqueta
"Simulado" visible en el panel) hasta que añadas uno — un DHT22 son ~4-5€ y
da humedad además de una segunda lectura de temperatura, si en algún momento
quieres completarlo.

**Aviso**: este código se ha escrito sin una placa delante — no se ha podido
probar en hardware real, solo compilar. Sigue la sección "Probar antes de
confiar en ello" antes de dejarlo funcionando solo.

## ⚠️ Seguridad: la resistencia de carga del sensor de corriente

El SCT-013-000 es un transformador de corriente "pelado": no trae
resistencia de carga (burden resistor) integrada, así que hay que soldar
una entre sus dos cables de salida, y es esa resistencia la que se conecta
al pin ADC del ESP32 — **nunca los cables del sensor directamente**.

Con este sensor (ratio 2000:1, hasta 100A) y una carga real de hasta 100A,
una resistencia de **4,7kΩ generaría hasta ~330V de pico** en el pin del
ESP32 — muy por encima de los 3,3V que soporta, lo freiría. Usa una
resistencia de **22-33Ω** (del kit de resistencias variadas que compraste,
busca un valor en esa década, no en kΩ). Esa 4,7kΩ del kit es la que sí
necesita el DS18B20, para el pull-up de su línea de datos — no sobra nada,
cada resistencia va a su sitio.

Si tienes dudas sobre qué resistencia estás cogiendo, mide con un polímetro
antes de soldar: debe marcar entre 22 y 33 ohmios, no miles de ohmios.

## Hardware

| Componente | Conexión al ESP32 |
|---|---|
| DS18B20 (temperatura) | VCC→3V3, GND→GND, DATA→GPIO4, con resistencia de **4,7kΩ** entre DATA y 3V3 (pull-up, obligatoria para OneWire) |
| ADXL345 (vibración) | VCC→3V3, GND→GND, SDA→GPIO21, SCL→GPIO22 (pines I2C por defecto del ESP32) |
| SCT-013-000 (consumo) | Los dos cables del sensor a una resistencia de carga de **22-33Ω**; esa resistencia conectada entre GPIO34 (ADC) y GND — **y el clamp de corriente alrededor del cable de fase de la nave, instalado por alguien con conocimientos eléctricos** |

Todos los sensores comparten alimentación 3.3V y masa con el ESP32; solo
cambian los pines de datos.

## Librerías a instalar (Arduino IDE → Gestor de Librerías)

- **OneWire** (Paul Stoffregen)
- **DallasTemperature** (Miles Burton)

El ADXL345 se lee por I2C directo con `Wire.h` y el sensor de corriente por
el ADC interno del ESP32 (`analogRead`) — ninguno de los dos necesita
librería extra.

## Configurar el sketch

Antes de subirlo, edita estas líneas en `esp32_nave.ino`:

```cpp
const char* WIFI_SSID = "TU_WIFI";
const char* WIFI_PASSWORD = "TU_CONTRASEÑA_WIFI";

SensorConfig SENSOR_TEMPERATURA = {0, "PON_AQUI_LA_API_KEY"};
SensorConfig SENSOR_VIBRACION   = {0, "PON_AQUI_LA_API_KEY"};
SensorConfig SENSOR_CONSUMO     = {0, "PON_AQUI_LA_API_KEY"};

const float BURDEN_OHMS = 27.0; // ajusta al valor real que hayas soldado (22-33)
```

### Cómo conseguir el `sensor_id` y la `api_key` de cada sensor

1. Entra en INDU-TWIN como admin → abre la nave donde vas a instalar el
   hardware.
2. En cada tarjeta de sensor (Temperatura, Vibración, Consumo eléctrico) hay
   un icono de llave 🔑 — púlsalo para ver la clave de ese sensor concreto.
   (La tarjeta de Humedad no la necesitas: ese sensor sigue en modo
   simulado porque no hay hardware para él en este kit.)
3. El `sensor_id` no se muestra en la interfaz todavía; sácalo así, con tu
   token de admin (Ajustes del navegador → pestaña Red, tras iniciar
   sesión, copia el header `Authorization` de cualquier petición):

   ```bash
   curl https://indu-twin-backend.onrender.com/api/buildings/<ID_DE_LA_NAVE>/sensors \
     -H "Authorization: Bearer <TU_TOKEN>"
   ```

   Esto devuelve los sensores de esa nave con su `id` y `sensor_type`
   (`temperature`, `humidity`, `vibration`, `energy`) — empareja cada uno
   con la clave que copiaste en el paso 2 (ignora el de `humidity`).

## Probar antes de confiar en ello

No subas el sketch completo a ciegas. Antes de montarlo en la nave:

1. **Prueba cada sensor por separado** con el monitor serie abierto
   (115200 baudios) — confirma que `ds18b20.getTempCByIndex(0)`, la lectura
   del ADXL345 y `readMainsCurrentRms()` imprimen números con sentido antes
   de conectarlos a INDU-TWIN.
2. **Mide la resistencia de carga con un polímetro** antes de dar corriente
   al circuito — debe estar entre 22 y 33Ω. Si tienes dudas, no conectes el
   ESP32 todavía.
3. **Prueba el envío HTTP con un solo sensor primero** — sube el sketch con
   solo `SENSOR_TEMPERATURA` configurado (deja los otros dos en
   `sensorId = 0`, así `sendReading` los omite automáticamente) y confirma
   en el panel de la nave que la lectura llega y se ve razonable.
4. **Calibra el sensor de corriente**: compara la corriente que muestra el
   monitor serie (`readMainsCurrentRms`) con una pinza amperimétrica real o
   con el contador de la nave durante un rato, y ajusta
   `CALIBRATION_FACTOR` hasta que los kWh que llegan a la app cuadren con el
   consumo real. Sin este paso, los números de energía son solo una
   aproximación razonable, no una medida fiable.
5. **Calibra el factor de vibración**: el número que manda el ADXL345 es una
   aproximación (`SCALE_TO_APPROX_MMS` en el código), no una medida
   industrial calibrada de mm/s. Con la máquina parada debería dar un valor
   bajo y estable; en marcha, más alto. Ajusta el factor de escala
   observando esos dos casos reales, no lo des por bueno tal cual.
6. Solo cuando los tres funcionen por separado y estén calibrados, deja el
   sketch completo corriendo solo.

## Ajustar la frecuencia de envío

`SEND_INTERVAL_MS` está puesto a 60 segundos — razonable para una nave real
(no hace falta la frecuencia de 15s del simulador, que solo existe para que
la demo se vea "viva"). Súbelo a 5 minutos o más si quieres ahorrar datos/
batería en un despliegue con muchos dispositivos.
