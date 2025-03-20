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

class MQTTClientHandler:
    def __init__(self, process_received_message=None):
        self.process_received_message = process_received_message or self.default_process_received_message

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"Connected with result code {str(rc)}")

    def on_disconnect(self, client, userdata, rc, properties=None):
        if rc != 0:
            print("Unexpected disconnection.")

    def on_publish(self, client, userdata, mid, properties=None):
        print(f"published: {mid}")

    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        print(f"Subscribed: {str(mid)} {str(granted_qos)}")

    def on_message(self, client, userdata, message):
        self.process_received_message(message)

    @staticmethod
    def default_process_received_message(message):
        def process_sensor_message(message):
            # Process message in XML format
            root = ET.fromstring(message)
            client_id = root.find("client_id").text
            sensor_id = root.find("sensor_id").text
            msg_id = root.find("msg_id").text
            value = root.find("value").text
            return client_id, sensor_id, msg_id, value
        payload = str(message.payload.decode("utf-8"))
        print(f"Received topic {message.topic}")
        try:
            ET.fromstring(payload)
            client_id, sensor_id, msg_id, value = process_sensor_message(payload)
            print(f"Received Client {client_id} sensor {sensor_id} msg_id {msg_id} temperature {value}")
        except ET.ParseError:
            print(f"Invalid XML payload: {payload}")
        except Exception as e:
            print(f"Unexpected error while processing payload: {payload}. Error: {e}")

    def unsubscribe_from_topics(self, client, topics):
        """Unsubscribe from a list of topics."""
        for topic in topics:
            client.unsubscribe(topic)
            print(f"Unsubscribed from topic: {topic}")
