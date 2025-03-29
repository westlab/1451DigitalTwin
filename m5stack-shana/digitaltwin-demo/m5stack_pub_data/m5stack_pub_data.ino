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

#include <M5Stack.h>
#include <M5UnitENV.h>
#include <WiFi.h>
#include <PubSubClient.h>
# include "time.h"

// constants
// loop delay
#define LOW_POWER_MODE true
#if LOW_POWER_MODE
const int loop_delay = 5000; // 5 seconds
const bool low_power_mode = true; // low power mode
#else
const int loop_delay = 1000; // 5 seconds
const bool low_power_mode = false; // low power mode
#endif

// device name
const char* device_name = "core_1";
// Wi-Fi settings
const char* ssid = "GL-AR750-310";
const char* password = "goodlife"; 
// mqtt settings
const char* mqtt_server = "192.168.8.101";
const int mqtt_port = 1883;
//String mqtt_topic_name = "_1451DT/" + (String)device_name + "/sensor/data";
String mqtt_topic_name = "_1451DT/" + (String)device_name + "/sensor/data";
// setup ntp and timezone
const char* ntpServer = "ntp.nict.jp";
const long  gmtOffset_sec = 3600 * 9;
const int   daylightOffset_sec = 0;

// global variables
struct tm timeinfo;
// handle sensor
SHT4X sht4;
BMP280 bmp;
// network
String ip_address;
//mqtt
WiFiClient esp_client;
PubSubClient mqttclient(esp_client);
// to write formatted messages
String formatted_mqtt_msg = "";
bool mqtt_publish_status = false;

void setupWifi(){
    Serial.println("starting wifi setup");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    ip_address = WiFi.localIP().toString();
    String formatted_serial_msg = "\ncompleted wifi setup\nSSID: " + String(ssid) + "\nLocal IP: " + ip_address;
    Serial.println(formatted_serial_msg);
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
    M5.Lcd.fillScreen(WHITE);
    delay(500);
    M5.Lcd.fillScreen(RED);
    delay(500);
    M5.Lcd.fillScreen(GREEN);
    delay(500);
    M5.Lcd.fillScreen(BLUE);
    delay(500);
    M5.Lcd.fillScreen(BLACK);
    delay(500);
    M5.Lcd.setCursor(10, 10);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.setTextSize(2);
    M5.Lcd.printf("Device: %s \n  ssid: %s\n  IP:%s", device_name, ssid, ip_address.c_str());
}

void setup() {
    M5.begin();
    M5.Power.begin();
    Serial.begin(115200);
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    setupSensor();
    setupWifi();
    mqttclient.setServer(mqtt_server, mqtt_port);
    mqttclient.connect(ip_address.c_str());
    if (low_power_mode){
        M5.Lcd.writecommand(ILI9341_DISPOFF);
        M5.Lcd.setBrightness(0);
    }
    else{
        setupDisplay();
    }  
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

String getLocalTimeString(){
    getLocalTime(&timeinfo);
    return String(timeinfo.tm_year + 1900) + "-" + String(timeinfo.tm_mon + 1) +
    "-" + String(timeinfo.tm_mday + 1) + "_" +
     String(timeinfo.tm_hour) + ":" + String(timeinfo.tm_min) + 
     ":" + String(timeinfo.tm_sec);
}

String generateFormattedMessage(){
    return "Device: " +  String(device_name) +
        "\n SSID:   " + String(ssid) +
        "\n IP:     " + String(ip_address) + 
        "\n MQTT:   " + String(mqtt_server) + ":"+ String(mqtt_port) +
        "\n  TOPIC: " + String(mqtt_topic_name) +
        "\n  CONN:  " + String(mqttclient.connected()) +
        "\n LocalTime:" + getLocalTimeString() +
        "\n TempSHT: " + String(sht4.cTemp) + 
        "\n Humidity:" + String(sht4.humidity) +
        "\n Pressure:" + String(bmp.pressure) +
        "\n Altitude:" + String(bmp.altitude) +
        "\n TempBMP: "+ String(bmp.cTemp);
}


String generateMQTTMessageJSON(){
    return "{ \"Device\":\"" +  String(device_name) +"\""+
        ",\"LocalTime\":\"" + getLocalTimeString() +"\""+
        ",\"TempSHT\":" + String(sht4.cTemp) +
        ",\"TempBMP\":"+ String(bmp.cTemp) +
        ",\"Humidity\":" + String(sht4.humidity) +
        ",\"Pressure\":" + String(bmp.pressure) +
        ",\"Altitude\":" + String(bmp.altitude) +
        "}";
}

String generateMQTTMessageXML(){
  //when xml is too long publish fails
    String xml_message = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>";
    xml_message += "<TEDS ID=\"[v03]\">";
    //xml_message += "<BasicTEDS>";
    //xml_message += "<Manufacturer>Dewesoft</Manufacturer>";
    //xml_message += "<Model>1</Model>";
    //xml_message += "<VersionLetter>A</VersionLetter>";
    //xml_message += "<VersionNumber>1</VersionNumber>";
    //xml_message += "<SerialNumber>1</SerialNumber>";
    //xml_message += "</BasicTEDS>";
    //xml_message += "<TEDS-Code length=\"40\">6A4000200401000098D0421F00000000 00000012040000120400001204000000 C34800000000E000</TEDS-Code>";
    //xml_message += "<Info-Section EditorVersion=\"Dewesoft TedsEditor V2.2.12\">";
    //xml_message += "<InfoLine16>2023/05/22 0:25:06: Templates cleared by User.</InfoLine16>";
    //xml_message += "<InfoLine17>2023/05/22 0:25:28: Base template [#38] Thermistor created.</InfoLine17>";
    //xml_message += "</Info-Section>";
    xml_message += "<DEBUG>";
    xml_message += "<DeviceName>" + String(device_name) + "</DeviceName>";
    //xml_message += "<LocalTime>" + getLocalTimeString() + "</LocalTime>";
    xml_message += "<TempSHT>" + String(sht4.cTemp) + "</TempSHT>";
    xml_message += "<TempBMP>" + String(bmp.cTemp) + "</TempBMP>";
    xml_message += "<Humidity>" + String(sht4.humidity) + "</Humidity>";
    xml_message += "<Pressure>" + String(bmp.pressure) + "</Pressure>";
    //xml_message += "<Altitude>" + String(bmp.altitude) + "</Altitude>";
    xml_message += "</DEBUG>";
    xml_message += "</TEDS>";
    return xml_message;
}

bool publishDataSerial(){
    Serial.println(generateFormattedMessage());
    return true;
}

bool publishDataDisplay(){
    M5.Lcd.setTextSize(2.0);
    M5.Lcd.setCursor(10, 10);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.printf(generateFormattedMessage().c_str());
    return true;
}

bool publishDataMQTT(){
    if (mqttclient.connected()) {
        const char* mqtt_message = generateMQTTMessageXML().c_str();
        mqttclient.publish(mqtt_topic_name.c_str(), mqtt_message);
        //mqttclient.publish(mqtt_topic_name.c_str(), generateMQTTMessageJSON().c_str());
        return true;
    }
    return false;
}

void loop() {
    static unsigned long last_display_update = 0; // Track the last display update time
    unsigned long current_time = millis();
    if (readSensor()) {
        if (publishDataMQTT()) {
            mqtt_publish_status = true;
        } else {
            mqtt_publish_status = false;
        }
        if (!mqttclient.connected()) {
            mqtt_publish_status = false;
            mqttclient.connect(ip_address.c_str());
        }
        // Update display only if 1 minute has passed
        if (low_power_mode){
        }
        else{
            publishDataSerial();
            if (current_time - last_display_update >= 60000) {
                publishDataDisplay();
                last_display_update = current_time;
            }
        }
        mqtt_publish_status = false;
    }
    else {
        Serial.println("Failed to read sensor data");
        mqtt_publish_status = false;
    }
    delay(loop_delay);
}