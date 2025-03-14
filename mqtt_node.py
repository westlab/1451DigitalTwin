#!/usr/bin/python
import paho.mqtt.client as paho
from paho import mqtt
import argparse
from time import sleep
import random
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description="MQTT Subscriber")
parser.add_argument("--mqtt_sub_topics", nargs='+', default=["OUCtest/yourID"], help="MQTT topics to subscribe to")
parser.add_argument("--mqtt_pub_topics", nargs='+', default=["OUCtest/yourID"], help="MQTT topics to publish to")
parser.add_argument("--mqtt_broker", default="broker.hivemq.com", help="MQTT broker address")
parser.add_argument("--mqtt_port", type=int, default=1883, help="MQTT broker port")
parser.add_argument("--mqtt_username", help="MQTT username for authentication")
parser.add_argument("--mqtt_password", help="MQTT password for authentication")
parser.add_argument("--client_id", default="client_1", help="Client ID for the MQTT connection")
parser.add_argument("--enable_tls", action="store_true", default=False, help="Enable TLS for MQTT connection")
parser.add_argument("--iterations", type=str, default="inf", help="Number of iterations for the while loop. Use 'infinity' for an infinite loop.")
args = parser.parse_args()

def on_connect(client, userdata, flags, rc, properties=None):
    # mqtt client call back for connect
    print(f"Connected with result code {str(rc)}")

def on_disconnect(client, userdata, rc):
    # mqtt client call back for disconnect
    if rc != 0:
        print("Unexpected disconnection.")

def on_publish(client, userdata, mid, properties=None):
    # mqtt client call back for publish
    print(f"published: {mid}")

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    # mqtt client call back for subscribe
    print(f"Subscribed: {str(mid)} {str(granted_qos)}")

def on_message(client, userdata, message):
    # mqtt client call back for message received
    process_received_data(message)

def process_received_data(message):
    # Updated logic to process the received XML data
    payload = str(message.payload.decode("utf-8"))
    print(f"Received topic {message.topic}")
    try:
        # Check if the payload is valid XML
        ET.fromstring(payload)
        client_id, sensor_id, value = process_sensor_message(payload)
        print(f"Received Client {client_id} sensor {sensor_id} temperature {value}")
    except ET.ParseError:
        print(f"Invalid XML payload: {payload}")
    except Exception as e:
        print(f"Unexpected error while processing payload: {payload}. Error: {e}")

def read_dummy_temp_sensor():
    """Simulates a temperature sensor with a linearly increasing value between 10-30 with noise.
    Returns:
        float: Temperature value or None if the sensor fails to read
    """
    if not hasattr(read_dummy_temp_sensor, "current_temp"):
        read_dummy_temp_sensor.current_temp = 10.0
    if random.choice([True, False]):
        noise = random.gauss(0, 1)
        read_dummy_temp_sensor.current_temp += 0.5
        read_dummy_temp_sensor.current_temp = min(read_dummy_temp_sensor.current_temp, 30.0)
        return round(read_dummy_temp_sensor.current_temp + noise, 2)
    return None

def prepare_sensor_message(client_id, sensor_id, value):
    # Prepare message in proper XML format with header
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<message>
    <client_id>{client_id}</client_id>
    <sensor_id>{sensor_id}</sensor_id>
    <value>{value}</value>
</message>"""

def process_sensor_message(message):
    # Process message in XML format
    root = ET.fromstring(message)
    client_id = root.find("client_id").text
    sensor_id = root.find("sensor_id").text
    value = root.find("value").text
    return client_id, sensor_id, value

def main():
    # setup MQTT client
    print(f"Setting up MQTT client")
    client = paho.Client(client_id=args.client_id, userdata=None, protocol=paho.MQTTv5)
    if args.enable_tls:
        client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    # Set username and password if provided
    if args.mqtt_username and args.mqtt_password:
        client.username_pw_set(args.mqtt_username, args.mqtt_password)
    # setup MQTT test callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    print(f"Connecting to MQTT client {args.mqtt_broker}:{args.mqtt_port}")
    # setup the client
    client.connect(args.mqtt_broker, args.mqtt_port, 60)
    # Assign subscribe topics
    sub_topics = args.mqtt_sub_topics if isinstance(args.mqtt_sub_topics, list) else [args.mqtt_sub_topics]
    # Assign publisher topics
    pub_topics = args.mqtt_pub_topics if isinstance(args.mqtt_pub_topics, list) else [args.mqtt_pub_topics]
    # subscript to topics
    print(f"Subscribing to topics {sub_topics}")
    for topic in sub_topics:
        client.subscribe(topic)
    print(f"Starting client loop")
    # start client loop
    client.loop_start()
    i = 0
    # iterations limit for CI
    iterations = float('inf') if "inf" in args.iterations.lower() else int(args.iterations)
    while i < iterations:
        i += 1
        # Your logic here
        # Publishing random temperature value to topic
        sensor_id = "temp_sensor1"
        temp_value = read_dummy_temp_sensor()
        if temp_value:
            for topic in pub_topics:
                pub_message = prepare_sensor_message(args.client_id, sensor_id, temp_value)
                client.publish(topic, f"{pub_message}")
                print(f"Published {pub_message} to topic {topic}")
        else:
            print(f"Failed to read the sensor")
        sleep(5)
    # stop the client loop
    client.loop_stop()

if __name__ == '__main__':
    main()
