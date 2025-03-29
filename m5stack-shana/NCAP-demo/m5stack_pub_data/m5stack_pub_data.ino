/** 
* @author W. A. Shanaka P. Abeysiriwardhana
* @copyright shanakaprageeth
* @version 0.0.1
* @date 2025-03-30
* @brief This is a demo program for M5Stack Core2
* @details This program is a demo for M5Stack Core2 and NCAP. It reads data from SHT4X sensor and publish it to MQTT server.
* @platform: m5stack core
* @sensor: SHT4X series sensor
**/

#include <M5Core2.h>
#include <M5UnitENV.h>
#include <WiFi.h>
#include <PubSubClient.h>

// constants
// device name
const char* device_name = "Core_1";
// Wi-Fi settings
const char* ssid = "GL-AR750-310";
const char* password = "goodlife"; 
// mqtt settings
const char* mqtt_server = "192.168.8.101";
const int mqtt_port = 1883;

// global variables
// handle sensor
SHT4X sht4;
BMP280 bmp;
// network
String ip_address;
//mqtt
WiFiClient espClient;
PubSubClient mqttclient(espClient);
// to write formatted messages
String formattedMessage = "";

void setupWifi(){
    Serial.println("starting wifi setup");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    ip_address = WiFi.localIP().toString();
    formattedMessage = "\ncompleted wifi setup\nSSID: " + String(ssid) + "\nLocal IP: " + ip_address;
    Serial.println(formattedMessage);
}

void setupSensor(){
    Serial.println("starting SHT4X sensor setup");
    if (!sht4.begin(&Wire, SHT40_I2C_ADDR_44, 21, 22, 400000U)) {
        Serial.println("Couldn't find SHT4x");
        while (1) delay(1);
    }

    // You can have 3 different precisions, higher precision takes longer
    sht4.setPrecision(SHT4X_HIGH_PRECISION);
    sht4.setHeater(SHT4X_NO_HEATER);

    if (!bmp.begin(&Wire, BMP280_I2C_ADDR, 21, 22, 400000U)) {
        Serial.println("Couldn't find BMP280");
        while (1) delay(1);
    }
    /* Default settings from datasheet. */
    bmp.setSampling(BMP280::MODE_NORMAL,     /* Operating Mode. */
                    BMP280::SAMPLING_X2,     /* Temp. oversampling */
                    BMP280::SAMPLING_X16,    /* Pressure oversampling */
                    BMP280::FILTER_X16,      /* Filtering. */
                    BMP280::STANDBY_MS_500); /* Standby time. */
    Serial.println("completed SHT4X sensor setup");
}

void setupDisplay(){
    M5.begin();
    M5.Lcd.setTextColor(WHITE, BLACK);
    M5.Lcd.setTextSize(2);
    M5.Lcd.setCursor(10, 10);
    M5.Lcd.printf("Device: %s \n  ssid: %s\n  IP:%s", device_name, ssid, ip_address.c_str());
    M5.Lcd.setTextSize(1);
}

void setup() {
    Serial.begin(115200);
    setupSensor();
    setupWifi();
    mqttclient.setServer(mqtt_server, mqtt_port);
    setupDisplay();
}

// Function to read sensor data
// Returns true if successful, false otherwise
// This function reads data from the SHT4X and BMP280 sensors
// sht4.cTemp is the temperature in Celsius
// sht4.humidity is the humidity in percentage
// bmp.cTemp is the temperature in Celsius
// bmp.pressure is the pressure in Pascal
// bmp.altitude is the altitude in meters
bool readSensor(){
    bool status = true;
    if (!sht4.update()){
        status = false;
    }
    if (!bmp.update()){
        status = false;
    }
    return status;
}

bool publishData(){
    if (mqttclient.connected()) {
        String message = "{\"device\":\"" + String(device_name) + "\",\"temperature\":" + String(sht4.cTemp) + ",\"humidity\":" + String(sht4.humidity) + "}";
        mqttclient.publish("sensor/data", message.c_str());
        return true;
    }
    return false;
}
void loop() {
    if (readSensor()) {
        formattedMessage = String("\nSensor Read complete") +
                           "\n  TempC:       " + String(sht4.cTemp) + 
                           "\n  Humidity:    " + String(sht4.humidity) +
                           "\n  Pressure:    " + String(bmp.pressure) +
                           "\n  Altitude:    " + String(bmp.altitude) +
                           "\n  Temperature: " + String(bmp.cTemp);
        Serial.println(formattedMessage);
    }
    else{
        Serial.println("Failed to read sensor data");
    }
    delay(1000);
}