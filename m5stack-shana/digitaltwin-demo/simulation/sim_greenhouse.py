#!/usr/bin/python
__author__ = "shanakaprageeth"

import paho.mqtt.client as paho
from paho import mqtt
import argparse
from time import sleep, time
import random
import xml.etree.ElementTree as ET
import sys
import threading
import json
from py_lib_digitaltwin.MQTTClientHandler import MQTTClientHandler
import csv
from datetime import datetime
import requests  # Add this import for making HTTP requests
import yaml

#TODO make and arg
store_data_csv=False


parser = argparse.ArgumentParser(description="Greenhouse simulator")
parser.add_argument("--config", help="Config file path", default="../config.yml")
args = parser.parse_args()

with open(args.config, "r") as config_file:
    config = yaml.safe_load(config_file)

# MQTT Configuration
MQTT_BROKER = config["mqtthost"]
MQTT_PORT = config["mqttport"]
MQTT_USERNAME = config.get("mqttusername",None)
MQTT_PASSWORD = config.get("mqttpassword",None)
MQTT_TLS = config.get("mqtt_tls", False)
SIM_ITERATIONS = config.get("iterations", "inf")
SIM_CITY = config.get("city", "Kawasaki")

# MQTT Topics
TOPIC_ALL_DATA = config["mqtt_topics"]["all_data"]
TOPIC_DT_CONTROL = config["mqtt_topics"]["digital_twin_control_input"]
TOPIC_DT_SENSOR_DATA = config["mqtt_topics"]["digital_twin_sensor_data"]
TOPIC_DT_HEATER_STATE = config["mqtt_topics"]["digital_twin_heater_state"]
TOPIC_HEATER_CONTROL = config["mqtt_topics"]["room_heater_control"]
TOPIC_HEATER_STATE = config["mqtt_topics"]["room_heater_state"]
TOPIC_CORE1_SENSOR_DATA = config["mqtt_topics"]["sensor_data_core_1"]
TOPIC_CORE2_SENSOR_DATA = config["mqtt_topics"]["sensor_data_core_2"]

TARGET_TEMPERATURE = config.get("target_temp",23)
DEADBAND = config.get("deadband",2)

def process_json_sensor_message(message):
    """Process message in JSON format."""
    try:
        data = json.loads(message)
        device_name = data.get("Device", "unknown")
        tempSHT = data.get("TempSHT", "unknown")
        tempBMP = data.get("TempBMP", "unknown")
        humidity = data.get("Humidity", "unknown")
        pressure = data.get("Pressure", "unknown")
        altitude = data.get("Altitude", "unknown")
        return device_name, tempSHT, tempBMP, humidity, pressure, altitude
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON payload")

def process_xml_sensor_message(message):
    # Process message in XML format
    root = ET.fromstring(message)
    debug = root.find("DEBUG")
    if debug is None:
        raise ValueError("DEBUG section not found in the XML payload")
    device_name = debug.find("DeviceName").text if debug.find("DeviceName") is not None else "unknown"
    tempSHT = debug.find("TempSHT").text if debug.find("TempSHT") is not None else "unknown"
    tempBMP = debug.find("TempBMP").text if debug.find("TempBMP") is not None else "unknown"
    humidity = debug.find("Humidity").text if debug.find("Humidity") is not None else "unknown"
    pressure = debug.find("Pressure").text if debug.find("Pressure") is not None else "unknown"
    altitude = debug.find("Altitude").text if debug.find("Altitude") is not None else "unknwon"  # Optional field
    return device_name, tempSHT, tempBMP, humidity, pressure, altitude

def get_json_sensor_message(device_name, tempSHT, tempBMP, humidity, pressure, altitude):
    """Constructs a JSON string with sensor data."""
    return f"""{{
        "Device": "{device_name}",
        "LocalTime": "{get_local_time_string()}",
        "TempSHT": {tempSHT},
        "TempBMP": {tempBMP},
        "Humidity": {humidity},
        "Pressure": {pressure},
        "Altitude": {altitude}
    }}"""

def get_local_time_string():
    """Returns the current local time as a string."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

def get_xml_sensor_message(device_name, tempSHT, tempBMP, humidity, pressure):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<TEDS>
    <DEBUG>
        <DeviceName>{device_name}</DeviceName>
        <LocalTime>"{get_local_time_string()}"</LocalTime>
        <TempSHT>{tempSHT:.2f}</TempSHT>
        <TempBMP>{tempBMP:.2f}</TempBMP>
        <Humidity>{humidity:.2f}</Humidity>
        <Pressure>{pressure:.2f}</Pressure>
    </DEBUG>
</TEDS>"""

def get_json_actuator_message(state):
    """Constructs a JSON string with sensor data."""
    return f"""{{
        "Type": "CMD",
        "LocalTime": "{get_local_time_string()}",
        "State": {state},
    }}"""

def request_sensor_data_message():
    data_request = f"""{{
        "Type": "REQ_DATA",
        "LocalTime": "{get_local_time_string()}",
    }}"""
    

def prepare_sensor_message(device_name, tempSHT, tempBMP, humidity, pressure, altitude=-10):
    # Prepare message in proper XML format with header
    #sensor_msg = get_json_sensor_message(device_name, tempSHT, tempBMP, humidity, pressure, altitude)
    sensor_msg = get_xml_sensor_message(device_name, tempSHT, tempBMP, humidity, pressure)
    return sensor_msg

# Global flag to prevent multiple executions of mqtt_test_async
mqtt_test_async_running = False
mqtt_test_async_lock = threading.Lock()  # Lock to prevent race conditions

def digital_twin_sim(
    mqtt_sub_topics=[TOPIC_ALL_DATA],
    mqtt_broker=MQTT_BROKER,
    mqtt_port=MQTT_PORT,
    mqtt_username=MQTT_USERNAME,
    mqtt_password=MQTT_PASSWORD,
    client_id="digitaltwin",
    enable_tls=MQTT_TLS,
    iterations=SIM_ITERATIONS,
):
    # setup MQTT client
    print(f"Setting up MQTT client")
    client = paho.Client(client_id=client_id, userdata=None, protocol=paho.MQTTv5)
    if enable_tls:
        client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    # Set username and password if provided
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)
    
    greenhouse = Greenhouse(
        mqtt_client=client,
        target_temperature=TARGET_TEMPERATURE,
        city=SIM_CITY,
        aircon_state=False,
        heater_state=False,
    )

    handler = MQTTClientHandler(greenhouse.process_received_message)
    client.on_connect = handler.on_connect
    client.on_disconnect = handler.on_disconnect
    client.on_publish = handler.on_publish
    client.on_message = handler.on_message
    client.on_subscribe = handler.on_subscribe

    print(f"Connecting to MQTT client {mqtt_broker}:{mqtt_port}")
    # setup the client
    client.connect(mqtt_broker, mqtt_port, 60)
    # Assign subscribe topics
    sub_topics = mqtt_sub_topics if isinstance(mqtt_sub_topics, list) else [mqtt_sub_topics]
    # subscribe to topics
    print(f"Subscribing to topics {sub_topics}")
    for topic in sub_topics:
        client.subscribe(topic)
    print(f"Starting client loop")
    client.loop_start()
    iterations = float('inf') if "inf" in iterations.lower() else int(iterations)
    i = 0
    last_sensor_data_iteration = 0
    while i < iterations:
        i += 1
        #print(f"Execution iteration {i}/{iterations}", flush=True)
        if i%(60*20) == 0:
            new_outside_temperature = get_current_temperature(greenhouse.city)
            if new_outside_temperature is not None:
                greenhouse.outside_temperature = new_outside_temperature
            print(f"Outside temperature: {greenhouse.outside_temperature}")
        if i % 60 == 0:
            if last_sensor_data_iteration == greenhouse.update_iteration:
                print(f"Sensor data not received for {i} iterations. Requesting sensor data.")
                greenhouse.request_sensor_data()
            last_sensor_data_iteration = greenhouse.update_iteration
        greenhouse.predict_system()
        greenhouse.publish_digital_twin()
        sleep(1)
    print("Stopping MQTT client loop", flush=True)
    client.loop_stop()
    client.disconnect()

class Greenhouse:
    def __init__(self, mqtt_client, target_temperature, city, aircon_state=False, heater_state=False, inside_temperature=None, dt_sensor_topic=TOPIC_DT_SENSOR_DATA, dt_actuator_topic=TOPIC_DT_HEATER_STATE, actuator_control_topic=TOPIC_HEATER_CONTROL):
        self.client = mqtt_client
        self.target_temperature = target_temperature
        self.target_humidity = 50
        self.target_pressure = 100000
        self.city = city
        self.outside_temperature = get_current_temperature(self.city)
        if self.outside_temperature is None:
            print(f"Error fetching outside temperature for {self.city}")
            assert inside_temperature is not None, "Inside temperature must be provided if outside temperature cannot be fetched."
            self.outside_temperature = inside_temperature
        self.aircon_state = aircon_state
        self.heater_state = heater_state
        self.inside_temperatureSHT = inside_temperature if inside_temperature is not None else self.outside_temperature
        self.inside_temperatureBMP = self.inside_temperatureSHT
        self.inside_pressure = 100000
        self.inside_humidity = 50
        self.kSHT = 0.5  # Gain of the system temperature
        self.kBMP = 0.5
        self.kHumidity = 0.001
        self.kPressure = 0.001
        self.tau = 10  # Time constant of the system
        self.time_step = 1  # Time step for simulation
        self.last_update_time = time()  # Track the last update time
        self.dt_sensor_topic = dt_sensor_topic
        self.dt_actuator_topic = dt_actuator_topic
        self.actuator_control_topic = actuator_control_topic
        self.update_iteration = 0
        self.prediction_iteration = 0
        self.activate_control = False

    def initial_setup(self):
        """Initial setup for the greenhouse simulator."""
        self.set_heater_state(False)
        self.set_aircon_state(False)

    def predict_system(self):
        """Predict the next inside conditions based on the FOPTD model."""
        current_time = time()
        elapsed_time = current_time - self.last_update_time
        self.last_update_time = current_time

        aircon_effect = -5 if self.aircon_state else 0
        heater_effect = 5 if self.heater_state else 0

        # Predict inside_temperatureSHT
        delta_temp_SHT = (self.kSHT * (self.target_temperature + aircon_effect + heater_effect - self.inside_temperatureSHT) +
                          (self.outside_temperature - self.inside_temperatureSHT) / self.tau) * elapsed_time
        self.inside_temperatureSHT += delta_temp_SHT

        # Predict inside_temperatureBMP
        delta_temp_BMP = (self.kBMP * (self.target_temperature + aircon_effect + heater_effect - self.inside_temperatureBMP) +
                          (self.outside_temperature - self.inside_temperatureBMP) / self.tau) * elapsed_time
        self.inside_temperatureBMP += delta_temp_BMP

        # Predict inside_humidity
        delta_humidity = self.kHumidity * (self.target_humidity - self.inside_humidity) * elapsed_time
        self.inside_humidity += delta_humidity

        # Predict inside_pressure
        delta_pressure = self.kPressure * (self.target_pressure - self.inside_pressure) * elapsed_time
        self.inside_pressure += delta_pressure

        # Correct predictions with actual data
        self.inside_humidity = max(0, min(100, self.inside_humidity))  # Ensure humidity stays within 0-100%
        self.inside_pressure = max(9000, min(200000, self.inside_pressure))  # Ensure pressure stays within realistic bounds
        print(f"Predicted conditions {self.prediction_iteration} {self.activate_control}: TempSHT: {self.inside_temperatureSHT:.2f}, TempBMP: {self.inside_temperatureBMP:.2f}, Humidity: {self.inside_humidity:.2f}, Pressure: {self.inside_pressure:.2f}, outside: {self.outside_temperature:.2f}, ")
        print(f"Gain values: kSHT: {self.kSHT:.2f}, kBMP: {self.kBMP:.2f}, kHumidity: {self.kHumidity:.2f}, kPressure: {self.kPressure:.2f}")
        print(f"Target temperature {self.target_temperature} inside temperature {self.inside_temperatureSHT}")
        if self.activate_control and (self.prediction_iteration % 60) == 0:
            if self.inside_temperatureSHT < self.target_temperature - DEADBAND:
                self.set_heater_state(True)
                self.set_aircon_state(False)
            elif self.inside_temperatureSHT > self.target_temperature + DEADBAND:
                self.set_heater_state(False)
                self.set_aircon_state(True)
            #else:
            #    self.set_heater_state(False)
            #    self.set_aircon_state(False)
        self.prediction_iteration += 1
        return self.inside_temperatureSHT, self.inside_temperatureBMP, self.inside_humidity, self.inside_pressure

    def update_model(self, actual_inside_temperatureSHT, actual_inside_temperatureBMP, actual_humidity):
        """Update the model parameters to correct the error."""
        # TODO no control for pressure and humidity set current value
        self.target_humidity = actual_humidity

        # Update for inside_temperatureSHT
        error_SHT = actual_inside_temperatureSHT - self.inside_temperatureSHT
        self.kSHT += 0.01 * error_SHT  # Adjust gain slightly based on error
        self.kSHT = min(5, self.kSHT) # Ensure gain stays within a reasonable range
        self.kSHT = max(-5, self.kSHT)
        self.tau = max(1, self.tau - 0.1 * error_SHT)  # Adjust time constant, ensuring it stays positive
        self.inside_temperatureSHT = actual_inside_temperatureSHT  # Correct the predicted temperature

        # Update for inside_temperatureBMP
        error_BMP = actual_inside_temperatureBMP - self.inside_temperatureBMP
        self.kBMP += 0.01 * error_BMP  # Adjust gain slightly based on error
        self.kBMP = min(5, self.kBMP)  # Ensure gain stays within a reasonable range
        self.kBMP = max(-5, self.kBMP)
        self.inside_temperatureBMP = actual_inside_temperatureBMP

        # Update for inside_humidity
        error_humidity = actual_humidity - self.inside_humidity
        self.kHumidity += 0.01 * error_humidity
        self.inside_humidity = actual_humidity

        print(f"Updated inside conditions: TempSHT: {self.inside_temperatureSHT:.2f}, TempBMP: {self.inside_temperatureBMP:.2f}, Humidity: {self.inside_humidity:.2f}, Pressure: {self.inside_pressure:.2f}, outside: {self.outside_temperature:.2f},")
        print(f"Updated Gain values: kSHT: {self.kSHT:.2f}, kBMP: {self.kBMP:.2f}, kHumidity: {self.kHumidity:.2f}, kPressure: {self.kPressure:.2f}")
        self.update_iteration += 1
        if self.update_iteration > 20:
            self.activate_control = True

    def request_sensor_data(self):
        payload = request_sensor_data_message()
        print(f"Requesting sensor data: {TOPIC_CORE1_SENSOR_DATA} {TOPIC_CORE2_SENSOR_DATA}  {payload}")
        self.client.publish(TOPIC_CORE1_SENSOR_DATA, payload)
        self.client.publish(TOPIC_CORE2_SENSOR_DATA, payload)

    def set_aircon_state(self, aircon_state):
        """Set the aircon state (on/off) during the simulation."""
        if self.aircon_state != aircon_state:
            self.aircon_state = aircon_state
            # TODO send signal to aircon

    def set_heater_state(self, heater_state):
        """Set the heater state (on/off) during the simulation."""
        if self.heater_state != heater_state:
            self.heater_state = heater_state
            if self.heater_state == True:
                payload = get_json_actuator_message("on")
            else:
                payload = get_json_actuator_message("off")
            #print(f"Publishing: {self.actuator_control_topic} {payload}")
            self.client.publish(self.actuator_control_topic, payload)
            print(f"Set heater state to {payload}")


    def publish_digital_twin(self):
        """Publish the current inside temperature to the specified MQTT topic."""
        sensor_msg = prepare_sensor_message("digitaltwin", self.inside_temperatureSHT, self.inside_temperatureBMP, self.inside_humidity, self.inside_pressure)
        ##print(f"Publishing:  {self.dt_sensor_topic} {sensor_msg}")
        self.client.publish(self.dt_sensor_topic, sensor_msg)
        if self.heater_state == True:
            payload = get_json_actuator_message("on")
        else:
            payload = get_json_actuator_message("off")
        #print(f"Publishing:  {self.dt_actuator_topic} {payload}")
        self.client.publish(self.dt_actuator_topic, payload)
        #print(f"Published temperature message to {self.dt_sensor_topic}")
    
    def process_received_message(self, message):
        payload = str(message.payload.decode("utf-8"))
        print(f"Received topic {message.topic}")
        if message.topic == TOPIC_CORE1_SENSOR_DATA or message.topic == TOPIC_CORE2_SENSOR_DATA :
            try:
                if payload.strip().startswith("{"):
                    device_name, tempSHT, tempBMP, humidity, pressure, altitude = process_json_sensor_message(payload)
                    print(f"Received Device {device_name} TempSHT {tempSHT} TempBMP {tempBMP} Humidity {humidity} Pressure {pressure} Altitude {altitude}")
                else:  # Assume XML format
                    ET.fromstring(payload)
                    device_name, tempSHT, tempBMP, humidity, pressure, altitude = process_xml_sensor_message(payload)
                    print(f"Received Device {device_name} TempSHT {tempSHT} TempBMP {tempBMP} Humidity {humidity} Pressure {pressure}")
                self.update_model(float(tempSHT), float(tempBMP), float(humidity))
                if store_data_csv:
                    csv_file_name = f"{device_name}.csv"
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    csv_data = [current_time, tempSHT, tempBMP, humidity, pressure, altitude]
                    with open(csv_file_name, mode='a', newline='') as file:
                        writer = csv.writer(file)
                        if file.tell() == 0:  # Write header if file is empty
                            writer.writerow(["Time", "TempSHT", "TempBMP", "Humidity", "Pressure", "Altitude"])
                        writer.writerow(csv_data)
            except (ET.ParseError, ValueError) as e:
                print(f"Invalid xml payload: {payload}. Error: {e}")
            except Exception as e:
                print(f"Unexpected error while processing payload: {payload}. Error: {e}")
        elif message.topic == TOPIC_DT_CONTROL:
            print(f"Received control input: {payload}")
            self.target_temperature = float(payload)
            print(f"Set target temperature : {self.target_temperature }")
        elif message.topic == TOPIC_HEATER_STATE:
            print(f"Received heater status: {payload}")
            if "on" in payload:
                self.heater_state = True
            elif "off" in payload:
                self.heater_state = False

def get_coordinates(city):
    """
    Fetch the latitude and longitude for a given city using a free geocoding API.
    This function uses the Open-Meteo Geocoding API, which does not require an API key.
    """
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            latitude = data["results"][0]["latitude"]
            longitude = data["results"][0]["longitude"]
            return latitude, longitude
        else:
            print(f"No results found for city: {city}")
            return None, None
    except requests.RequestException as e:
        print(f"Error fetching coordinates for {city}: {e}")
        return None, None

def get_current_temperature(city):
    """
    Fetch the current temperature for a given city using a free weather API.
    This function uses the Open-Meteo API, which does not require authentication.
    """
    try:
        latitude, longitude = get_coordinates(city)
        if latitude is None or longitude is None:
            return None
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP issues
        data = response.json()
        temperature = data["current_weather"].get("temperature")
        if isinstance(temperature, (int, float)):  # Ensure the temperature is a valid float or int
            print(f"Current temperature in {city}: {temperature}°C")
            return float(temperature)
        else:
            print(f"Invalid temperature data for {city}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching temperature for {city}: {e}")
        return None
    except KeyError:
        print(f"Unexpected response format while fetching temperature for {city}")
        return None

if __name__ == '__main__':
    digital_twin_sim(
        mqtt_sub_topics=[TOPIC_ALL_DATA],
        mqtt_broker=MQTT_BROKER,
        mqtt_port=MQTT_PORT,
        mqtt_username=MQTT_USERNAME,
        mqtt_password=MQTT_PASSWORD,
        client_id="digitaltwin",
        enable_tls=MQTT_TLS,
        iterations=SIM_ITERATIONS,
    )
