#!/usr/bin/python
__author__ = "shanakaprageeth"

from time import sleep
from switchbot import SwitchBot
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
token =''
secret = ''

#TODO make and arg
store_data_csv=False


parser = argparse.ArgumentParser(description="MQTT Subscriber")
parser.add_argument("--mqtt_sub_topics", nargs='+', default=["_1451DT/room/heater/#"], help="MQTT topics to subscribe to")
parser.add_argument("--mqtt_broker", default="192.168.8.101", help="MQTT broker address")
parser.add_argument("--mqtt_port", type=int, default=1883, help="MQTT broker port")
parser.add_argument("--mqtt_username", help="MQTT username for authentication")
parser.add_argument("--mqtt_password", help="MQTT password for authentication")
parser.add_argument("--client_id", default="room_heater", help="Client ID for the MQTT connection")
parser.add_argument("--enable_tls", action="store_false", default=False, help="Enable TLS for MQTT connection")
parser.add_argument("--iterations", type=str, default="inf", help="Number of iterations for the while loop. Use 'infinity' for an infinite loop.")
args = parser.parse_args()

def turn_on_heater():
    switchbot = SwitchBot(token=token, secret=secret)
    bot = switchbot.device(id='C9690A9783EC')
    plug = switchbot.device(id='34B7DAD4C62E')
    plug.command('turn_off')
    sleep(1)
    plug.command('turn_on')
    sleep(1)
    bot.press()
    print("Heater turned on")

def turn_off_heater():
    switchbot = SwitchBot(token=token, secret=secret)
    bot = switchbot.device(id='C9690A9783EC')
    plug = switchbot.device(id='34B7DAD4C62E')
    bot.press()
    sleep(1)
    plug.command('turn_off')
    print("Heater turned off")

def my_process_received_message(message):
    payload = str(message.payload.decode("utf-8"))
    print(f"Received topic {message.topic} {payload}")
    if message.topic == "_1451DT/room/heater/control":
        if "on" in payload:
            turn_on_heater()
        elif "off" in payload:
            turn_off_heater()

def get_local_time_string():
    """Returns the current local time as a string."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d_%H:%M:%S")


# Global flag to prevent multiple executions of mqtt_test_async
mqtt_test_async_running = False
mqtt_test_async_lock = threading.Lock()  # Lock to prevent race conditions

def digital_twin_sim(
    mqtt_sub_topics=["_1451DT/#"],
    mqtt_broker="192.168.8.101",
    mqtt_port=1883,
    mqtt_username=None,
    mqtt_password=None,
    client_id="room_heater",
    enable_tls=False,
    iterations="inf",
):
    turn_off_heater()
    sleep(20)
    print(f"Starting program")
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
        try:
            switchbot = SwitchBot(token=token, secret=secret)
            plug = switchbot.device(id='34B7DAD4C62E')
            client.publish("_1451DT/room/heater/state", str(plug.status()['power']), qos=1)
        except Exception as e:
            print(f"Error: {e}", flush=True)
        sleep(60)
    print("Stopping MQTT client loop", flush=True)
    client.loop_stop()
    client.disconnect()


if __name__ == '__main__':
    digital_twin_sim(
        mqtt_sub_topics=args.mqtt_sub_topics,
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        client_id=args.client_id,
        enable_tls=args.enable_tls,
        iterations=args.iterations
    )

