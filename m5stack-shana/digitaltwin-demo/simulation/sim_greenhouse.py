#!/usr/bin/python
__author__ = "shanakaprageeth"

import paho.mqtt.client as paho
from paho import mqtt
import argparse
from time import sleep
import random
import xml.etree.ElementTree as ET
import sys
import threading
import json
from shanaka.MQTTClientHandler import MQTTClientHandler
import csv
from datetime import datetime

parser = argparse.ArgumentParser(description="MQTT Subscriber")
parser.add_argument("--mqtt_sub_topics", nargs='+', default=["_1451DT/#"], help="MQTT topics to subscribe to")
parser.add_argument("--mqtt_pub_topics", nargs='+', default=["_1451DT/sim_1/sensor/data"], help="MQTT topics to publish to")
parser.add_argument("--mqtt_broker", default="192.168.8.101", help="MQTT broker address")
parser.add_argument("--mqtt_port", type=int, default=1883, help="MQTT broker port")
parser.add_argument("--mqtt_username", help="MQTT username for authentication")
parser.add_argument("--mqtt_password", help="MQTT password for authentication")
parser.add_argument("--client_id", default="sim_1", help="Client ID for the MQTT connection")
parser.add_argument("--enable_tls", action="store_false", default=False, help="Enable TLS for MQTT connection")
parser.add_argument("--iterations", type=str, default="inf", help="Number of iterations for the while loop. Use 'infinity' for an infinite loop.")
args = parser.parse_args()

def process_received_message(message):
    payload = str(message.payload.decode("utf-8"))
    print(f"Received topic {message.topic}")
    if message.topic == "_1451DT/core_1/sensor/data" or message.topic == "_1451DT/core_1/sensor/data" or 
        message.topic == "_1451DT/sim/sensor/data":
        try:
            if payload.strip().startswith("{"):  # Assume JSON format
                device_name, tempSHT, tempBMP, humidity, pressure, altitude = process_json_sensor_message(payload)
                print(f"Received Device {device_name} TempSHT {tempSHT} TempBMP {tempBMP} Humidity {humidity} Pressure {pressure} Altitude {altitude}")
            else:  # Assume XML format
                ET.fromstring(payload)
                device_name, tempSHT, tempBMP, humidity, pressure = process_xml_sensor_message(payload)
                altitude = "N/A"  # Default value if altitude is not provided in XML
                print(f"Received Device {device_name} TempSHT {tempSHT} TempBMP {tempBMP} Humidity {humidity} Pressure {pressure}")
            # TODO error correction for digital twin
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
            print(f"Invalid payload: {payload}. Error: {e}")
        except Exception as e:
            print(f"Unexpected error while processing payload: {payload}. Error: {e}")
    elif message.topic == "_1451DT/twin/control/input":
        print(f"Received control input: {payload}")
        # TODO process control input
        # TODO calculate current digital twin greenhouse temperature
        # TODO calculate difference between current and target temperature
        # TODO send aircon on/off or heater on/off state on digital twin model
        # TODO send the control input to real actuator with mqtt


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
    return device_name, tempSHT, tempBMP, humidity, pressure

def read_dummy_temp_sensor(client, pub_topics, client_id):
    """Simulates a temperature sensor with a linearly increasing value between 10-30 with noise.
    Publishes the data to the client if available.
    """
    sensor_id = "temp_sensor1"
    if not hasattr(read_dummy_temp_sensor, "current_temp"):
        read_dummy_temp_sensor.current_temp = 10.0
    if not hasattr(read_dummy_temp_sensor, "msg_id"):
        read_dummy_temp_sensor.msg_id = 1
    noise = random.gauss(0, 1)
    read_dummy_temp_sensor.current_temp += 0.5
    read_dummy_temp_sensor.current_temp = min(read_dummy_temp_sensor.current_temp, 30.0)
    temp_value = round(read_dummy_temp_sensor.current_temp + noise, 2)
    msg_id = read_dummy_temp_sensor.msg_id
    for topic in pub_topics:
        # TODO replace dummy values
        pub_message = prepare_sensor_message(device_name='twin', tempSHT=20, tempBMP=20, humidity=50, pressure=10000, altitude=-10)
        client.publish(topic, f"{pub_message}")
    read_dummy_temp_sensor.msg_id += 1

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
        <TempSHT>{tempSHT}</TempSHT>
        <TempBMP>{tempBMP}</TempBMP>
        <Humidity>{humidity}</Humidity>
        <Pressure>{pressure}</Pressure>
    </DEBUG>
</TEDS>"""

def prepare_sensor_message(device_name, tempSHT, tempBMP, humidity, pressure, altitude=-10):
    # Prepare message in proper XML format with header
    #sensor_msg = get_json_sensor_message(device_name, tempSHT, tempBMP, humidity, pressure, altitude)
    sensor_msg = get_xml_sensor_message(device_name, tempSHT, tempBMP, humidity, pressure)
    return sensor_msg

# Global flag to prevent multiple executions of mqtt_test_async
mqtt_test_async_running = False
mqtt_test_async_lock = threading.Lock()  # Lock to prevent race conditions

def mqtt_test(
    mqtt_sub_topics=["_1451DT/#"],
    mqtt_pub_topics=["_1451DT/sim/sensor/data"],
    mqtt_broker="192.168.8.101",
    mqtt_port=1883,
    mqtt_username=None,
    mqtt_password=None,
    client_id="sim_1",
    enable_tls=False,
    iterations="inf",
    process_received_message=None
):
    # setup MQTT client
    print(f"Setting up MQTT client")
    client = paho.Client(client_id=client_id, userdata=None, protocol=paho.MQTTv5)
    if enable_tls:
        client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    # Set username and password if provided
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)

    handler = MQTTClientHandler(process_received_message)
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
    # Assign publisher topics
    pub_topics = mqtt_pub_topics if isinstance(mqtt_pub_topics, list) else [mqtt_pub_topics]
    # subscribe to topics
    print(f"Subscribing to topics {sub_topics}")
    for topic in sub_topics:
        client.subscribe(topic)
    print(f"Starting client loop")
    client.loop_start()

    iterations = float('inf') if "inf" in args.iterations.lower() else int(args.iterations)
    i = 0
    while True:
        pass
    '''
    while i < iterations:
        i += 1
        print(f"Execution iteration {i}/{iterations}", flush=True)
        read_dummy_temp_sensor(client, pub_topics, client_id)
        sleep(5)
    '''
    print("Stopping MQTT client loop", flush=True)
    client.loop_stop()
    client.disconnect()

from time import time  # Add this import for real-time tracking

class Greenhouse:
    def __init__(self, target_temperature, outside_temperature, aircon_on, heater_on=False, inside_temperature=None):
        self.target_temperature = target_temperature
        self.outside_temperature = outside_temperature
        self.aircon_on = aircon_on
        self.heater_on = heater_on
        self.inside_temperature = inside_temperature if inside_temperature is not None else outside_temperature
        self.k = 0.5  # Gain of the system
        self.tau = 10  # Time constant of the system
        self.time_step = 1  # Time step for simulation
        self.last_update_time = time()  # Track the last update time

    def predict_temperature(self):
        """Predict the next inside temperature based on the FOPTD model."""
        current_time = time()
        elapsed_time = current_time - self.last_update_time
        self.last_update_time = current_time

        aircon_effect = -5 if self.aircon_on else 0
        heater_effect = 5 if self.heater_on else 0
        delta_temp = (self.k * (self.target_temperature + aircon_effect + heater_effect - self.inside_temperature) +
                      (self.outside_temperature - self.inside_temperature) / self.tau) * elapsed_time
        self.inside_temperature += delta_temp
        return self.inside_temperature

    def update_model(self, actual_inside_temperature):
        """Update the model parameters to correct the error."""
        error = actual_inside_temperature - self.inside_temperature
        self.k += 0.01 * error  # Adjust gain slightly based on error
        self.tau = max(1, self.tau - 0.1 * error)  # Adjust time constant, ensuring it stays positive
        self.inside_temperature = actual_inside_temperature  # Correct the predicted temperature

    def set_aircon_state(self, aircon_on):
        """Set the aircon state (on/off) during the simulation."""
        self.aircon_on = aircon_on

    def set_heater_state(self, heater_on):
        """Set the heater state (on/off) during the simulation."""
        self.heater_on = heater_on

if __name__ == '__main__':
    mqtt_test(
        mqtt_sub_topics=args.mqtt_sub_topics,
        mqtt_pub_topics=args.mqtt_pub_topics,
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        client_id=args.client_id,
        enable_tls=args.enable_tls,
        iterations=args.iterations
    )
