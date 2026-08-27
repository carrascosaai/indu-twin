/*
  INDU-TWIN — firmware para una nave (ESP32)
  ============================================
  Lee temperatura, humedad, vibracion y consumo electrico, y manda cada
  lectura a INDU-TWIN via POST /api/ingest/reading — el mismo endpoint que
  usa el simulador interno, asi que el backend no distingue entre un dato
  simulado y uno real.

  AVISO IMPORTANTE: este codigo no se ha podido probar en una placa fisica
  (se ha escrito sin hardware delante). Antes de dejarlo funcionando solo en
  una nave real, prueba cada sensor por separado con el monitor serie
  abierto y confirma que los valores que imprime tienen sentido.

  Hardware necesario (ver también firmware/esp32_nave/README.md):
    - ESP32 DevKit
    - DHT22 / AM2302 (temperatura + humedad) -> pin definido en DHT_PIN
    - ADXL345 (vibracion, por I2C)           -> SDA/SCL por defecto del ESP32
    - PZEM-004T v3.0 (consumo electrico, por UART) -> pines PZEM_RX/PZEM_TX

  Librerias a instalar desde el Gestor de Librerias del IDE Arduino:
    - "DHT sensor library" (Adafruit)
    - "Adafruit Unified Sensor" (dependencia de la anterior)
    - "PZEM004Tv30" (de Jakub Mandula)
  (ADXL345 se lee por I2C directo con Wire.h, que ya viene incluido — no
  hace falta instalar nada para ese sensor.)
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <DHT.h>
#include <PZEM004Tv30.h>

// ---------------------------------------------------------------------
// CONFIGURACION — rellena esto con tus datos antes de subir el sketch
// ---------------------------------------------------------------------

// WiFi de la nave
const char* WIFI_SSID = "TU_WIFI";
const char* WIFI_PASSWORD = "TU_CONTRASEÑA_WIFI";

// Backend de INDU-TWIN. No hace falta cambiarlo salvo que uses tu propio
// despliegue distinto al de produccion.
const char* API_BASE_URL = "https://indu-twin-backend.onrender.com";

// IDs y claves de cada sensor: se sacan del icono de llave (🔑) en el panel
// de la nave dentro de la app (solo lo ve un admin). El sensor_id se ve en
// GET /api/buildings/{id}/sensors si lo prefieres por API.
struct SensorConfig {
  int sensorId;
  const char* apiKey;
};

SensorConfig SENSOR_TEMPERATURA = {0, "PON_AQUI_LA_API_KEY"};
SensorConfig SENSOR_HUMEDAD     = {0, "PON_AQUI_LA_API_KEY"};
SensorConfig SENSOR_VIBRACION   = {0, "PON_AQUI_LA_API_KEY"};
SensorConfig SENSOR_CONSUMO     = {0, "PON_AQUI_LA_API_KEY"};

// Cada cuanto se manda una lectura de cada sensor. La app funciona bien con
// datos cada 1-5 minutos para una nave real (no hace falta la frecuencia
// del simulador, que es solo para que la demo se vea "viva").
const unsigned long SEND_INTERVAL_MS = 60UL * 1000UL; // 60s

// Pines
#define DHT_PIN 4
#define DHT_TYPE DHT22
#define PZEM_RX 16 // al TX del PZEM
#define PZEM_TX 17 // al RX del PZEM

// ---------------------------------------------------------------------

DHT dht(DHT_PIN, DHT_TYPE);
PZEM004Tv30 pzem(Serial2, PZEM_RX, PZEM_TX);

const uint8_t ADXL345_ADDR = 0x53;
float lastEnergyKwh = -1.0; // -1 = todavia no hemos leido el contador

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\nINDU-TWIN — firmware de nave arrancando...");

  dht.begin();
  Wire.begin();
  initAdxl345();

  connectWifi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
  }

  readAndSendTemperatureHumidity();
  readAndSendVibration();
  readAndSendEnergy();

  Serial.printf("Esperando %lus hasta la proxima ronda de lecturas...\n", SEND_INTERVAL_MS / 1000);
  delay(SEND_INTERVAL_MS);
}

// ---------------------------------------------------------- WiFi ----

void connectWifi() {
  Serial.printf("Conectando a WiFi \"%s\"...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(400);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nConectado. IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\nNo se pudo conectar al WiFi. Se reintentara en el siguiente ciclo.");
  }
}

// ---------------------------------------------------- Envio HTTP ----

bool sendReading(const SensorConfig& sensor, float value) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Sin WiFi, no se manda la lectura.");
    return false;
  }
  if (sensor.sensorId <= 0) {
    Serial.println("sensor_id sin configurar, se omite este sensor.");
    return false;
  }

  WiFiClientSecure client;
  // El backend esta en Render con un certificado publico normal, pero
  // validar la cadena completa desde un ESP32 es mas lio del que merece la
  // pena para un piloto: se salta la verificacion del certificado. Si esto
  // pasa a produccion "de verdad" con datos sensibles, hay que cargar el
  // certificado raiz real con client.setCACert(...).
  client.setInsecure();

  HTTPClient http;
  String url = String(API_BASE_URL) + "/api/ingest/reading";
  if (!http.begin(client, url)) {
    Serial.println("No se pudo iniciar la peticion HTTP.");
    return false;
  }
  http.addHeader("Content-Type", "application/json");

  char body[192];
  snprintf(body, sizeof(body),
           "{\"sensor_id\":%d,\"api_key\":\"%s\",\"value\":%.3f}",
           sensor.sensorId, sensor.apiKey, value);

  int status = http.POST((uint8_t*)body, strlen(body));
  bool ok = (status == 201);
  Serial.printf("POST sensor_id=%d value=%.3f -> HTTP %d %s\n",
                sensor.sensorId, value, status, ok ? "OK" : "ERROR");
  if (!ok && status > 0) {
    Serial.println(http.getString());
  }
  http.end();
  return ok;
}

// ------------------------------------------------- Temp / Humedad ----

void readAndSendTemperatureHumidity() {
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();

  if (isnan(temp) || isnan(hum)) {
    Serial.println("Lectura del DHT22 invalida, se salta esta ronda.");
    return;
  }

  sendReading(SENSOR_TEMPERATURA, temp);
  sendReading(SENSOR_HUMEDAD, hum);
}

// ------------------------------------------------------ Vibracion ----

void initAdxl345() {
  // POWER_CTL (0x2D): bit 3 (Measure) a 1 para salir del modo standby.
  writeAdxlRegister(0x2D, 0x08);
  // DATA_FORMAT (0x31): +/-16g, resolucion completa.
  writeAdxlRegister(0x31, 0x0B);
}

void writeAdxlRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(ADXL345_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

// Lee ~100 muestras en un segundo y calcula cuanto se aleja la aceleracion
// de 1g (reposo). Es una aproximacion pensada para detectar maquinaria
// vibrando de forma anomala, NO una medida calibrada de mm/s de verdad —
// para eso haria falta un sensor de vibracion industrial con acondicionado
// de señal propio. Sirve para que las reglas de alerta de INDU-TWIN (que
// comparan contra un umbral) tengan una señal razonable.
float readVibrationMagnitude() {
  const int samples = 100;
  double sumSquares = 0;

  for (int i = 0; i < samples; i++) {
    int16_t raw[3];
    if (readAdxlSample(raw)) {
      // Sensibilidad a +/-16g y resolucion completa: ~3.9 mg por bit.
      float gx = raw[0] * 0.0039f;
      float gy = raw[1] * 0.0039f;
      float gz = raw[2] * 0.0039f;
      float magnitude = sqrt(gx * gx + gy * gy + gz * gz);
      float deviation = magnitude - 1.0f; // 1g = en reposo
      sumSquares += deviation * deviation;
    }
    delay(10);
  }

  float rms = sqrt(sumSquares / samples);
  // Factor de escala arbitrario para que el numero caiga en un rango
  // parecido al que usan los umbrales por defecto de la app (mm/s).
  // Ajusta ESTE FACTOR observando valores reales con la maquina parada vs.
  // en marcha, no lo des por bueno tal cual.
  const float SCALE_TO_APPROX_MMS = 40.0f;
  return rms * SCALE_TO_APPROX_MMS;
}

bool readAdxlSample(int16_t out[3]) {
  Wire.beginTransmission(ADXL345_ADDR);
  Wire.write(0x32); // DATAX0
  if (Wire.endTransmission(false) != 0) return false;

  if (Wire.requestFrom(ADXL345_ADDR, (uint8_t)6) != 6) return false;
  uint8_t raw[6];
  for (int i = 0; i < 6; i++) raw[i] = Wire.read();

  out[0] = (int16_t)(raw[1] << 8 | raw[0]);
  out[1] = (int16_t)(raw[3] << 8 | raw[2]);
  out[2] = (int16_t)(raw[5] << 8 | raw[4]);
  return true;
}

void readAndSendVibration() {
  float vibration = readVibrationMagnitude();
  sendReading(SENSOR_VIBRACION, vibration);
}

// ---------------------------------------------------------- Consumo ----

void readAndSendEnergy() {
  float totalKwh = pzem.energy();
  if (isnan(totalKwh)) {
    Serial.println("No se pudo leer el PZEM-004T (revisa cableado UART).");
    return;
  }

  if (lastEnergyKwh < 0) {
    // Primera lectura: solo fijamos la referencia, no mandamos nada
    // todavia porque no hay "delta" que calcular.
    lastEnergyKwh = totalKwh;
    Serial.printf("Lectura inicial del PZEM: %.3f kWh acumulados.\n", totalKwh);
    return;
  }

  float deltaKwh = totalKwh - lastEnergyKwh;
  if (deltaKwh < 0) {
    // El PZEM se reinicio (corte de luz, reset manual...): re-sincroniza
    // sin mandar un valor negativo.
    lastEnergyKwh = totalKwh;
    return;
  }

  // INDU-TWIN espera, en cada lectura de un sensor de energia, el consumo
  // ocurrido DESDE la lectura anterior (no el acumulado total) — asi es
  // como lo genera tambien el simulador interno.
  sendReading(SENSOR_CONSUMO, deltaKwh);
  lastEnergyKwh = totalKwh;
}
