#!/bin/bash -eu

echo "Running MQTT Node Test"
# TODO move password to secret
python3 mqtt_node.py \
        --mqtt_sub_topic test \
        --mqtt_pub_topic test \
        --mqtt_port 8883 \
        --mqtt_broker 3277bbbd24e24f328e93456f6a9f1602.s1.eu.hivemq.cloud \
        --mqtt_username ci-runner \
        --mqtt_password cirunner1A \
        --enable_tls --iterations 2 | tee output.log

cat output.log

if ! grep -q "Received Client" output.log; then
    echo "Error: Subscription message not received"
    exit 1
else
    echo "Test Passed"
    exit 0
fi
