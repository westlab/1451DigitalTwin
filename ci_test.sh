#!/bin/bash -ex
# author ShanakaPrageeth
# details executing Github Actions CI/CD pipeline

DEBIAN_FRONTEND=noninteractive
PROGRAM_NAME="$(basename $0)"
BASEDIR=$(dirname $(realpath "$0"))

export PYTHONPATH=$BASEDIR:$PYTHONPATH

unittests() {
    echo "Executing tox tests"
    tox
}

systemtests(){
    cd $BASEDIR/examples
    echo "======Running System Tests====="
    echo "Running Config Reader Test"
    python3 config_reader_example.py $BASEDIR/config.yml | tee output.log
    if ! grep -q "Configuration loaded successfully" output.log; then
        echo "Error: Configuration failed to load"
        exit 1
    else
        echo "Test Passed"
        exit 0
    fi
    echo "Running MQTT Node Test"
    # TODO move password to secret
    python3 mqtt_test_example.py \
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
}

if [[ $# -eq 0 ]]; then
    echo "No argument provided. Defaulting to 'all'. Options are: unittests, systemtests, all"
    set -- all
fi

case "$1" in
    unittests)
        unittests
        ;;
    systemtests)
        systemtests
        ;;
    all)
        unittests
        systemtests
        ;;
    *)
        echo "Invalid argument: $1"
        echo "Usage: $PROGRAM_NAME {unittests|systemtests|all}"
        exit 1
        ;;
esac
