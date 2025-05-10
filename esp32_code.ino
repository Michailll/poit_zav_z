#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>

#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>

#include <WiFi.h>
#include <time.h>
const char* ssid = "d201";
const char* password = "MechaTronyka";

// const char* serverUrl = "http://192.168.100.89:80/upload";
const char* serverUrl = "http://192.168.11.140:80/upload";
AsyncWebServer server(8080);


#define DHTPIN 2
#define DHTTYPE DHT11
#define PIRPIN 5

DHT_Unified dht(DHTPIN, DHTTYPE);
bool measuring = false;
bool prevPIR = LOW;


String getTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) return String("");
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", &timeinfo);
  return String(buf);
}

void sendJsonData(float t, float h, const String& ts) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");
  StaticJsonDocument<200> doc;
  doc["cmd"] = "data";
  doc["temp"] = t;
  doc["hum"] = h;
  doc["ts"] = ts;
  String body;
  serializeJson(doc, body);
  int code = http.POST(body);
  Serial.printf("POST code: %d\n", code);
  http.end();
}

void sendJsonStatus(const String& ts, bool measuring) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");
  StaticJsonDocument<100> doc;
  doc["cmd"] = "status";
  doc["measuring"] = measuring;
  doc["ts"] = ts;
  String body;
  serializeJson(doc, body);
  int code = http.POST(body);
  Serial.printf("POST code: %d\n", code);
  http.end();
}


void setup() {
  Serial.begin(115200);
  pinMode(PIRPIN, INPUT);
  dht.begin();
  Serial.println("ESP32 booted");

  WiFi.begin(ssid, password);
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  while (WiFi.status() != WL_CONNECTED) delay(500);
  delay(1000);  

  sendJsonStatus(getTimestamp(), measuring);

 
  server.on("/toggle", HTTP_GET, [](AsyncWebServerRequest* req) {
    measuring = !measuring;
    StaticJsonDocument<100> doc;
    doc["measuring"] = measuring;
    doc["ts"] = getTimestamp();
    String body;
    serializeJson(doc, body);

    AsyncWebServerResponse* resp = req->beginResponse(200, "application/json", body);
    resp->addHeader("Access-Control-Allow-Origin", "*");
    resp->addHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
    resp->addHeader("Access-Control-Allow-Headers", "Content-Type");
    req->send(resp);
  });

  server.on("/toggle", HTTP_OPTIONS, [](AsyncWebServerRequest* req) {
    AsyncWebServerResponse* resp = req->beginResponse(204);
    resp->addHeader("Access-Control-Allow-Origin", "*");
    resp->addHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
    resp->addHeader("Access-Control-Allow-Headers", "Content-Type");
    req->send(resp);
  });

  Serial.println("WiFi.localIP()");
  Serial.println(WiFi.localIP());
  server.begin();
}

void loop() {
  bool curr = digitalRead(PIRPIN);
  if (curr && !prevPIR) {
    measuring = !measuring;
  }
  prevPIR = curr;

  if (measuring) {
    sensors_event_t e;
    dht.temperature().getEvent(&e);
    float t = e.temperature;
    dht.humidity().getEvent(&e);
    float h = e.relative_humidity;
    if (!isnan(t) && !isnan(h)) {
      sendJsonData(t, h, getTimestamp());
    }
  } else {
    sendJsonStatus(getTimestamp(), measuring);
  }

  delay(2000);
}