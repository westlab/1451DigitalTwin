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

def my_process_received_message(message):
    payload = str(message.payload.decode("utf-8"))
    print(f"Received topic {message.topic}")
    try:
        if payload.strip().startswith("{"):  # Assume JSON format
            device_name, tempSHT, tempBMP, humidity, pressure, altitude = process_json_sensor_message(payload)
            print(f"Received Device {device_name} TempSHT {tempSHT} TempBMP {tempBMP} Humidity {humidity} Pressure {pressure} Altitude {altitude}")
        else:  # Assume XML format
            ET.fromstring(payload)
            device_name, tempSHT, tempBMP, humidity, pressure = process_xml_sensor_message(payload)
            print(f"Received Device {device_name} TempSHT {tempSHT} TempBMP {tempBMP} Humidity {humidity} Pressure {pressure}")
    except (ET.ParseError, ValueError) as e:
        print(f"Invalid payload: {payload}. Error: {e}")
    except Exception as e:
        print(f"Unexpected error while processing payload: {payload}. Error: {e}")

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
        pub_message = prepare_sensor_message(device_name='sim_1', tempSHT=20, tempBMP=20, humidity=50, pressure=10000, altitude=-10)
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

    handler = MQTTClientHandler(my_process_received_message)
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
    while i < iterations:
        i += 1
        print(f"Execution iteration {i}/{iterations}", flush=True)
        read_dummy_temp_sensor(client, pub_topics, client_id)
        sleep(5)

    print("Stopping MQTT client loop", flush=True)
    client.loop_stop()
    client.disconnect()

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
