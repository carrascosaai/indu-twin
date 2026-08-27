/*
  INDU-TWIN — firmware para una nave (ESP32)
  ============================================
  Version para este kit de hardware concreto:
    - DS18B20 (temperatura, por OneWire — protocolo distinto al DHT)
    - ADXL345 (vibracion, por I2C)
    - SCT-013-000 100A + resistencia de carga propia (consumo, por el ADC
      del ESP32 — NO lleva chip PZEM, aqui se calcula todo a mano)

  AVISO IMPORTANTE: este codigo no se ha podido probar en una placa fisica
  (se ha escrito sin hardware delante). Antes de dejarlo funcionando solo,
  prueba cada sensor por separado con el monitor serie — ver README.md.

  ESTE KIT NO TRAE SENSOR DE HUMEDAD. La app sigue esperando una lectura de
  humedad para la nave, pero como no hay hardware real para ella, esa
  tarjeta se queda mostrando datos del simulador para siempre (ahora se ve
  claramente en el panel de la nave, con la etiqueta "Simulado") — no es un
  error, es el estado honesto hasta que añadas un sensor de humedad barato
  (un DHT22 son ~4€ y da humedad ademas de otra lectura de temperatura).

  --------------------------------------------------------------------
  ATENCION AL CABLEADO DEL SENSOR DE CORRIENTE (SCT-013-000):
  El SCT-013-000 es un transformador de corriente "pelado" (sin resistencia
  de carga incorporada, a diferencia del SCT-013-030). Necesita una
  resistencia de carga ("burden resistor") ENTRE sus dos cables de salida,
  y es ESA resistencia la que se lee con el ADC — nunca conectes el sensor
  directamente al pin del ESP32.

  Con un SCT-013-000 de 100A (ratio 2000:1) y el ADC del ESP32 (0-3.3V):
  una resistencia de carga de 4.7kΩ generaria hasta ~330V de pico con
  carga alta — freiria el ESP32. Usa algo en el rango de 22-33Ω (revisa el
  kit de resistencias variadas que hayas comprado; el valor exacto no es
  critico, pero tiene que estar en esas decenas de ohmios, NO en kΩ).
  BURDEN_OHMS mas abajo tiene que coincidir con la resistencia real que
  sueldes.
  --------------------------------------------------------------------

  Hardware necesario (ver tambien firmware/esp32_nave/README.md):
    - ESP32 DevKitC 38 pines
    - DS18B20 (temperatura) -> pin ONEWIRE_PIN, con resistencia de 4.7kΩ
      entre el cable de datos y 3V3 (pull-up)
    - ADXL345 (vibracion, por I2C) -> SDA/SCL por defecto del ESP32
    - SCT-013-000 + resistencia de carga de 22-33Ω -> pin ADC_PIN (ver
      aviso de arriba antes de conectar nada)

  Librerias a instalar desde el Gestor de Librerias del IDE Arduino:
    - "OneWire" (Paul Stoffregen)
    - "DallasTemperature" (Miles Burton)
  (ADXL345 se lee por I2C directo con Wire.h, y el sensor de corriente por
  el ADC interno del ESP32 — ninguno de los dos necesita libreria extra.)
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>

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
// GET /api/buildings/{id}/sensors si lo prefieres por API. No hay entrada
// de humedad porque este kit no trae sensor para ella (ver aviso arriba).
struct SensorConfig {
  int sensorId;
  const char* apiKey;
};

SensorConfig SENSOR_TEMPERATURA = {0, "PON_AQUI_LA_API_KEY"};
SensorConfig SENSOR_VIBRACION   = {0, "PON_AQUI_LA_API_KEY"};
SensorConfig SENSOR_CONSUMO     = {0, "PON_AQUI_LA_API_KEY"};

// Cada cuanto se manda una lectura de cada sensor. La app funciona bien con
// datos cada 1-5 minutos para una nave real (no hace falta la frecuencia
// del simulador, que es solo para que la demo se vea "viva").
const unsigned long SEND_INTERVAL_MS = 60UL * 1000UL; // 60s

// Pines
#define ONEWIRE_PIN 4     // DS18B20
#define ADC_PIN 34        // SCT-013-000 (pin ADC1, entrada analogica pura)

// Parametros del sensor de corriente — AJUSTA ESTO A TU RESISTENCIA REAL
const float BURDEN_OHMS = 27.0;       // resistencia de carga soldada (22-33Ω)
const float SCT_TURNS_RATIO = 2000.0; // SCT-013-000: 2000:1 (100A : 50mA)
const float ADC_VREF = 3.3;           // referencia del ADC del ESP32
const float MAINS_VOLTAGE = 230.0;    // tension de red asumida (España)
// Si los kWh que aparecen en la app no cuadran con un contador real,
// calibra multiplicando por (valor_real / valor_leido) hasta que encajen.
const float CALIBRATION_FACTOR = 1.0;

// ---------------------------------------------------------------------

OneWire oneWire(ONEWIRE_PIN);
DallasTemperature ds18b20(&oneWire);

const uint8_t ADXL345_ADDR = 0x53;
float lastEnergyKwh = -1.0; // -1 = todavia no hemos hecho la primera medida
unsigned long lastEnergyMillis = 0;

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\nINDU-TWIN — firmware de nave arrancando...");

  ds18b20.begin();
  Wire.begin();
  initAdxl345();
  analogReadResolution(12); // 0-4095, valor por defecto del ESP32 pero explicito

  lastEnergyMillis = millis();
  connectWifi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
  }

  readAndSendTemperature();
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

// ------------------------------------------------------- Temperatura ----

void readAndSendTemperature() {
  ds18b20.requestTemperatures();
  float temp = ds18b20.getTempCByIndex(0);

  if (temp == DEVICE_DISCONNECTED_C) {
    Serial.println("DS18B20 no responde (revisa el pull-up de 4.7kΩ y el cableado).");
    return;
  }

  sendReading(SENSOR_TEMPERATURA, temp);
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
//
// El SCT-013-000 no da un numero directo: hay que samplear el pin ADC
// muchas veces durante al menos un ciclo de red completo (20ms a 50Hz),
// calcular el RMS de la señal (quitando el offset de continua que mete el
// circuito de polarizacion), convertirlo a corriente real con la resistencia
// de carga y el ratio de vueltas del sensor, y de ahi a potencia asumiendo
// la tension de red. Es una estimacion, no una medida de precision de
// laboratorio — para eso haria falta un chip dedicado tipo PZEM-004T.

float readMainsCurrentRms() {
  const int samples = 2000; // varios ciclos de red a 50Hz
  long sum = 0;
  int minVal = 4095, maxVal = 0;

  // Primera pasada: centro (offset de continua) de la señal.
  int readings[samples];
  for (int i = 0; i < samples; i++) {
    readings[i] = analogRead(ADC_PIN);
    sum += readings[i];
    if (readings[i] < minVal) minVal = readings[i];
    if (readings[i] > maxVal) maxVal = readings[i];
    delayMicroseconds(150);
  }
  float mid = sum / (float)samples;

  // Segunda pasada: RMS de la desviacion respecto al centro.
  double sumSquares = 0;
  for (int i = 0; i < samples; i++) {
    float deviation = readings[i] - mid;
    sumSquares += deviation * deviation;
  }
  float rmsAdc = sqrt(sumSquares / samples);

  float rmsVoltageAtAdc = (rmsAdc / 4095.0f) * ADC_VREF;
  float rmsCurrentSecondary = rmsVoltageAtAdc / BURDEN_OHMS;
  float rmsCurrentPrimary = rmsCurrentSecondary * SCT_TURNS_RATIO;

  return rmsCurrentPrimary * CALIBRATION_FACTOR;
}

void readAndSendEnergy() {
  unsigned long now = millis();
  float currentA = readMainsCurrentRms();
  float powerW = currentA * MAINS_VOLTAGE;

  // kWh consumidos desde la ULTIMA lectura (no el acumulado): potencia
  // media estimada por el tiempo transcurrido, igual que hace el
  // simulador interno de INDU-TWIN para este mismo tipo de sensor.
  float hoursElapsed = (now - lastEnergyMillis) / 3600000.0f;
  float kwhThisInterval = (powerW / 1000.0f) * hoursElapsed;
  lastEnergyMillis = now;

  if (lastEnergyKwh < 0) {
    // Primera ronda: no hay intervalo real detras, no mandamos nada
    // todavia para no inventar un consumo de golpe.
    lastEnergyKwh = 0;
    Serial.printf("Corriente inicial: %.2f A (%.0f W). Primera lectura de energia omitida.\n",
                  currentA, powerW);
    return;
  }

  sendReading(SENSOR_CONSUMO, kwhThisInterval);
}
