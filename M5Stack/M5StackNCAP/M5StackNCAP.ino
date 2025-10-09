#include <M5Core2.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "SensirionI2cScd4x.h"
#include <Wire.h>

// Wi-Fi設定
const char* ssid = "westexp-mobile";
const char* password = "kyouryokunawestnohashi";

// MQTTブローカー設定
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;

// Device name（MACアドレスから自動生成）
String device_name;
String topic_name;

SensirionI2cScd4x scd4x;

// MQTT client
WiFiClient espClient;
PubSubClient client(espClient);

// グラフ設定
#define GRAPH_WIDTH  268
#define GRAPH_HEIGHT 48
#define GRAPH_X      42

#define GRAPH_SPACING 5

// 各グラフとキャプションのY座標を定義
#define CAPTION_CO2_Y   35
#define GRAPH_CO2_Y     (CAPTION_CO2_Y + 10)
#define CAPTION_TEMP_Y  (GRAPH_CO2_Y + GRAPH_HEIGHT + GRAPH_SPACING)
#define GRAPH_TEMP_Y    (CAPTION_TEMP_Y + 10)
#define CAPTION_HUM_Y   (GRAPH_TEMP_Y + GRAPH_HEIGHT + GRAPH_SPACING)
#define GRAPH_HUM_Y     (CAPTION_HUM_Y + 10)

float co2_values[GRAPH_WIDTH];
float temp_values[GRAPH_WIDTH];
float hum_values[GRAPH_WIDTH];

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect(device_name.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" 5秒後に再試行します");
      delay(5000);
    }
  }
}

void setup() {
  M5.begin();
  Serial.begin(115200);
  while (!Serial) {
    delay(100);
  }

  // MACアドレスから下位16ビットを取得してデバイス名を生成
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char mac_suffix[5];
  sprintf(mac_suffix, "%02X%02X", mac[4], mac[5]);
  device_name = "Core2_" + String(mac_suffix);
  
  topic_name = "_IECON_Plugfest/" + device_name + "/sample";

  Serial.print("Device Name: ");
  Serial.println(device_name);
  Serial.print("Topic Name: ");
  Serial.println(topic_name);

  // ディスプレイの初期化
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setTextColor(WHITE, BLACK);
  M5.Lcd.setTextSize(2);
  M5.Lcd.setCursor(10, 10);
  M5.Lcd.printf("Device: %s", device_name.c_str());

  setup_wifi();

  client.setServer(mqtt_server, mqtt_port);

  Wire.begin();

  uint16_t error;
  char errorMessage[256];

  scd4x.begin(Wire, 0x62);

  error = scd4x.stopPeriodicMeasurement();
  if (error) {
    Serial.print("Error trying to execute stopPeriodicMeasurement(): ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
  }

  uint64_t serialNumber;
  error = scd4x.getSerialNumber(serialNumber);
  if (error) {
    Serial.print("Error trying to execute getSerialNumber(): ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
  } else {
    Serial.print("Serial: 0x");
    Serial.println(serialNumber, HEX);
  }

  error = scd4x.startPeriodicMeasurement();
  if (error) {
    Serial.print("Error trying to execute startPeriodicMeasurement(): ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
  }

  Serial.println("Waiting for first measurement... (5 sec)");

  // グラフデータの初期化
  for (int i = 0; i < GRAPH_WIDTH; i++) {
    co2_values[i] = 0;
    temp_values[i] = 0;
    hum_values[i] = 0;
  }

  M5.Lcd.setTextSize(1);
  M5.Lcd.setTextColor(WHITE, BLACK);

  // CO2グラフ（枠を1ピクセル外側に描画）
  M5.Lcd.setCursor(GRAPH_X, CAPTION_CO2_Y);
  M5.Lcd.print("CO2 Concentration (ppm)");
  M5.Lcd.drawRect(GRAPH_X - 2, GRAPH_CO2_Y - 2, GRAPH_WIDTH + 4, GRAPH_HEIGHT + 4, WHITE);
  M5.Lcd.setCursor(5, GRAPH_CO2_Y);
  M5.Lcd.print("5000");
  M5.Lcd.setCursor(5, GRAPH_CO2_Y + GRAPH_HEIGHT / 2 - 4);
  M5.Lcd.print("2500");
  M5.Lcd.setCursor(15, GRAPH_CO2_Y + GRAPH_HEIGHT - 8);
  M5.Lcd.print("0");

  // 温度グラフ（枠を1ピクセル外側に描画）
  M5.Lcd.setCursor(GRAPH_X, CAPTION_TEMP_Y);
  M5.Lcd.print("Temperature (C)");
  M5.Lcd.drawRect(GRAPH_X - 2, GRAPH_TEMP_Y - 2, GRAPH_WIDTH + 4, GRAPH_HEIGHT + 4, WHITE);
  M5.Lcd.setCursor(15, GRAPH_TEMP_Y);
  M5.Lcd.print("40");
  M5.Lcd.setCursor(15, GRAPH_TEMP_Y + GRAPH_HEIGHT / 2 - 4);
  M5.Lcd.print("15");
  M5.Lcd.setCursor(10, GRAPH_TEMP_Y + GRAPH_HEIGHT - 8);
  M5.Lcd.print("-10");

  // 湿度グラフ（枠を1ピクセル外側に描画）
  M5.Lcd.setCursor(GRAPH_X, CAPTION_HUM_Y);
  M5.Lcd.print("Humidity (%)");
  M5.Lcd.drawRect(GRAPH_X - 2, GRAPH_HUM_Y - 2, GRAPH_WIDTH + 4, GRAPH_HEIGHT + 4, WHITE);
  M5.Lcd.setCursor(10, GRAPH_HUM_Y);
  M5.Lcd.print("100");
  M5.Lcd.setCursor(15, GRAPH_HUM_Y + GRAPH_HEIGHT / 2 - 4);
  M5.Lcd.print("50");
  M5.Lcd.setCursor(15, GRAPH_HUM_Y + GRAPH_HEIGHT - 8);
  M5.Lcd.print("0");
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  uint16_t error;
  char errorMessage[256];

  delay(100);

  uint16_t co2 = 0;
  float temperature = 0.0f;
  float humidity = 0.0f;
  bool isDataReady = false;
  error = scd4x.getDataReadyStatus(isDataReady);
  if (error) {
    Serial.print("Error trying to execute getDataReadyStatus(): ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
    return;
  }
  if (!isDataReady) {
    return;
  }
  error = scd4x.readMeasurement(co2, temperature, humidity);
  if (error) {
    Serial.print("Error trying to execute readMeasurement(): ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
  } else if (co2 == 0) {
    Serial.println("Invalid sample detected, skipping.");
  } else {
    Serial.print("Co2:");
    Serial.print(co2);
    Serial.print("\t");
    Serial.print("Temperature:");
    Serial.print(temperature);
    Serial.print("\t");
    Serial.print("Humidity:");
    Serial.println(humidity);

    // グラフデータを左にシフト
    for (int i = 0; i < GRAPH_WIDTH - 1; i++) {
      co2_values[i] = co2_values[i + 1];
      temp_values[i] = temp_values[i + 1];
      hum_values[i] = hum_values[i + 1];
    }
    co2_values[GRAPH_WIDTH - 1] = co2;
    temp_values[GRAPH_WIDTH - 1] = temperature;
    hum_values[GRAPH_WIDTH - 1] = humidity;

    // グラフエリアをクリア（枠の内側のみ）
    M5.Lcd.fillRect(GRAPH_X, GRAPH_CO2_Y, GRAPH_WIDTH, GRAPH_HEIGHT, BLACK);
    M5.Lcd.fillRect(GRAPH_X, GRAPH_TEMP_Y, GRAPH_WIDTH, GRAPH_HEIGHT, BLACK);
    M5.Lcd.fillRect(GRAPH_X, GRAPH_HUM_Y, GRAPH_WIDTH, GRAPH_HEIGHT, BLACK);

    // CO2グラフの描画
    for (int i = 0; i < GRAPH_WIDTH - 1; i++) {
      int y1 = GRAPH_CO2_Y + GRAPH_HEIGHT - (co2_values[i] / 5000.0) * GRAPH_HEIGHT;
      int y2 = GRAPH_CO2_Y + GRAPH_HEIGHT - (co2_values[i + 1] / 5000.0) * GRAPH_HEIGHT;
      M5.Lcd.drawLine(GRAPH_X + i, y1, GRAPH_X + i + 1, y2, GREEN);
    }

    // 温度グラフの描画
    for (int i = 0; i < GRAPH_WIDTH - 1; i++) {
      int y1 = GRAPH_TEMP_Y + GRAPH_HEIGHT - ((temp_values[i] + 10) / 50.0) * GRAPH_HEIGHT;
      int y2 = GRAPH_TEMP_Y + GRAPH_HEIGHT - ((temp_values[i + 1] + 10) / 50.0) * GRAPH_HEIGHT;
      M5.Lcd.drawLine(GRAPH_X + i, y1, GRAPH_X + i + 1, y2, RED);
    }

    // 湿度グラフの描画
    for (int i = 0; i < GRAPH_WIDTH - 1; i++) {
      int y1 = GRAPH_HUM_Y + GRAPH_HEIGHT - (hum_values[i] / 100.0) * GRAPH_HEIGHT;
      int y2 = GRAPH_HUM_Y + GRAPH_HEIGHT - (hum_values[i + 1] / 100.0) * GRAPH_HEIGHT;
      M5.Lcd.drawLine(GRAPH_X + i, y1, GRAPH_X + i + 1, y2, BLUE);
    }

    // 最新の値を表示
    M5.Lcd.setTextColor(WHITE, BLACK);
    M5.Lcd.fillRect(10, GRAPH_HUM_Y + GRAPH_HEIGHT + 12, 300, 20, BLACK);
    M5.Lcd.setCursor(10, GRAPH_HUM_Y + GRAPH_HEIGHT + 12);
    M5.Lcd.printf("Keio Univ. WestLab  CO2:%d Temp:%.1fC Hum:%.1f%%", co2, temperature, humidity);

    // MQTTメッセージの送信
    char mqttMessage[128];
    snprintf(mqttMessage, sizeof(mqttMessage), "{\"device\":\"%s\",\"co2\":%d,\"temperature\":%.2f,\"humidity\":%.2f}", device_name.c_str(), co2, temperature, humidity);

    if (client.connected()) {
      if (!client.publish(topic_name.c_str(), mqttMessage)) {
        Serial.println("Failed to publish MQTT message");
      } else {
        Serial.println("MQTT message published");
      }
    } else {
      Serial.println("MQTT client not connected");
    }
  }
}