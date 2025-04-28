#!/usr/bin/python3
# -*- coding: utf-8 -*- 
from time import sleep
import paho.mqtt.client as mqtt
import os
import struct 
import binascii
import sys
import yaml
import argparse
import uuid
import io
import csv
import pprint
import datetime
import temporenc
import RPi.GPIO as GPIO
import dht11
import time
import random

parser = argparse.ArgumentParser(
    prog = 'NCAP.py',
    usage = 'Receive BLE sensor data and send to MQTT server',
    description= 'PRISM demo for ALPS Smart IoT BLE Sensor module\nYou have to install and Bluetooth modules',
    epilog = 'Programmer: Hiroaki Nishi west@west.yokohama',
    add_help = True)
parser.add_argument('--version', version='%(prog)s 0.1',
    action = 'version',
    help = 'verbose operation (output sensor data)')
parser.add_argument('-v', '--verbose',
    action = 'store_true',
    help = 'verbose operation (output sensor data)',
    default = False)
parser.add_argument('-p', '--pseudo',
    action = 'store_true',
    help = 'pseudo sensors (generate random data as sensors)',
    default = False)
parser.add_argument('-q', '--quiet',
    action = 'store_true',
    help = 'quiet (does not output data messages)',
    default = False)
parser.add_argument('-c', '--config',
    action = 'store',
    help = 'specify YAML config file',
    default = './config.yml',
    type = str)
parser.add_argument('-d', '--ddisable',
    action = 'store_true',
    help = 'D disable (disable D messages)',
    default = False)

args = parser.parse_args()
vflag = False
if args.verbose:
    vflag = True
qflag = False
if args.quiet:
    qflag = True
sqflag = False
pflag = False
if args.pseudo:
    pflag = True
dflag = True
if args.ddisable:
    dflag = False

f = open(args.config, "r+")
confdata = yaml.safe_load(f)

if pflag == False:
    print('GPIO.set')
    print('Sensor')
    GPIO.setwarnings(True)
    GPIO.setmode(GPIO.BCM)
    print('Servo')
    GPIO.setup(4, GPIO.OUT)
    p = GPIO.PWM(4, 50)
    p.start(0.0)
else:
    print('Pseudo Sensors')

if not confdata.get('spfx'):
    confdata['spfx'] = '_1451.1.6/'
if not confdata.get('tomdop'):
    confdata['tomdop'] = 'D/'
if not confdata.get('tomcop'):
    confdata['tomcop'] = 'C/'
if not confdata.get('tomd0op'):
    confdata['tomd0op'] = 'D0/'
if not confdata.get('loc'):
    confdata['loc'] = 'LOC-NCAP-SERVER'
if not confdata.get('locclient'):
    confdata['locclient'] = 'LOC-NCAP-CLIENT'
topicdanno = confdata['spfx']+confdata['tomdop']+'.A/'+confdata['ncapname'] # publish
topicdannorecv = confdata['spfx']+confdata['tomdop']+'.A/#' # subscribe
topiccanno = confdata['spfx']+confdata['tomcop']+'.A/'+confdata['ncapname'] # publish
topiccannorecv = confdata['spfx']+confdata['tomcop']+'.A/#' # subscribe
topicdop = confdata['spfx']+confdata['tomdop']+confdata['loc']+'/'+confdata['ncapname'] # publish
topiccop = confdata['spfx']+confdata['tomcop']+confdata['loc']+'/'+confdata['ncapname'] # subscribe
topiccopres = confdata['spfx']+confdata['tomcop']+confdata['locclient']+'/'+confdata['appname'] # publish
topicd0op = confdata['spfx']+confdata['tomd0op']+confdata['loc']+'/'+confdata['ncapname'] # subscribe
topicd0opres = confdata['spfx']+confdata['tomd0op']+confdata['locclient']+'/'+confdata['ncapname'] # publish
if not confdata.get('TEMPTEDS'):
    confdata['TEMPTEDS'] = 'TEMPTEDS';
if not confdata.get('HUMIDTEDS'):
    confdata['HUMIDTEDS'] = 'HUMIDTEDS';
if not confdata.get('SERVOTEDS'):
    confdata['SERVOTEDS'] = 'SERVOTEDS';
if not confdata.get('TEMPBINTEDS'):
    confdata['TEMPBINTEDS'] = 'TEMPBINTEDS';
if not confdata.get('HUMIDTEDS'):
    confdata['HUMIDBINTEDS'] = 'HUMIDBINTEDS';
if not confdata.get('SERVOTEDS'):
    confdata['SERVOBINTEDS'] = 'SERVOBINTEDS';
#'_1451.1.6(SPFX)/D0(TOM)/LOC'
print("Topics for subscribe")
pprint.pprint([topiccop, topicd0op])
print("Topics for publish")
pprint.pprint([topiccopres, topicd0opres])

vhumid = {}
vtemp = {}

#binblk_anno = {
#    'netSvcType'        : {'offset': 0, 'type': '<B'}, #1
#    'netSvcId'          : {'offset': 1, 'type': '<B'}, #1
#    'msgType'           : {'offset': 2, 'type': '<B'}, #3
#    'msgLength'         : {'offset': 3, 'type': '<H'},
#    'ncapId'            : {'offset': 5, 'type': '<16s'},
#    'ncapName'          : {'offset': 21, 'type': '<16s'},
#    'addressType'       : {'offset': 37, 'type': '<B'}, #1 IPv4
#    'ncapAddress'       : {'offset': 38, 'type': '<4B'},
#}

#binblk_tim_announcement = {
#    'netSvcType'        : {'offset' : 0, 'type': '<B'}, #1
#    'netSvcId'          : {'offset' : 1, 'type': '<B'}, #2
#    'msgType'           : {'offset' : 2, 'type': '<B'}, #3
#    'msgLength'         : {'offset' : 3, 'type': '<H'},
#    'ncapId'            : {'offset' : 5, 'type': '<16s'},
#    'timId'             : {'offset' : 21, 'type': '<16s'},
#    'timName'           : {'offset' : 37, 'type': '<16s'},
#}

#binblk_tim_transducer_announcement = {
#    'netSvcType'        : {'offset' : 0, 'type': '<B'}, #1
#    'netSvcID'          : {'offset' : 1, 'type': '<B'}, #3
#    'msgType'           : {'offset' : 2, 'type': '<B'}, #3
#    'msgLength'         : {'offset' : 3, 'type': '<H'},
#    'ncapId'            : {'offset' : 5, 'type': '<16s'},
#    'timId'             : {'offset' : 21, 'type': '<16s'},
#    'transducerChannelId'   : {'offset' : 37, 'type': '<16s'},
#    'transducerChannelName' : {'offset' : 53, 'type': '<16s'},
#}

binblk_discovery_cmd = {
    'netSvcType'        : {'offset' : 0, 'type': '<B'}, #1
    'netSvcId'          : {'offset' : 1, 'type': '<B'}, #4
    'msgType'           : {'offset' : 2, 'type': '<B'}, #1
    'msgLength'         : {'offset' : 3, 'type': '<H'},
    'appId'             : {'offset' : 5, 'type': '<16s'},
    'timeout'           : {'offset' : 21, 'type': '<Q'},
}

#binblk_discovery_rep = {
#    'netSvcType'        : {'offset' : 0, 'type': '<B'}, #1
#    'netSvcId'          : {'offset' : 1, 'type': '<B'}, #4
#    'msgType'           : {'offset' : 2, 'type': '<B'}, #2
#    'msgLength'         : {'offset' : 3, 'type': '<H'},
#    'errorCode'         : {'offset' : 5, 'type': '<H'},
#    'appId'             : {'offset' : 7, 'type': '<16s'},
#    'ncapId'            : {'offset' : 23, 'type': '<16s'},
#    'ncapName'          : {'offset' : 39, 'type': '<16s'},
#    'addressType'       : {'offset' : 55, 'type': '<B'}, #1 IPv4
#    'ncapAddress'       : {'offset' : 56, 'type': '<4B'},
#}

binblk_tim_discovery_cmd = {
    'netSvcType'        : {'offset' : 0, 'type': '<B'}, #1
    'netSvcId'          : {'offset' : 1, 'type': '<B'}, #5
    'msgType'           : {'offset' : 2, 'type': '<B'}, #1
    'msgLength'         : {'offset' : 3, 'type': '<H'},
    'ncapId'            : {'offset' : 5, 'type': '<16s'},
    'timeout'           : {'offset' : 21, 'type': '<Q'},
}

#binblk_tim_discovery_rep = {
#    'netSvcType'        : {'offset' : 0, 'type': '<B'}, #1
#    'netSvcId'          : {'offset' : 1, 'type': '<B'}, #5
#    'msgType'           : {'offset' : 2, 'type': '<B'}, #2
#    'msgLength'         : {'offset' : 3, 'type': '<H'},
#    'errorCode'         : {'offset' : 5, 'type': '<H'},
#    'numOfTims'         : {'offset' : 7, 'type': '<2s'}, #num = 3
#    'timIds'            : {'offset' : 9, 'type': '<48s'}, #array x 3
#    'timNames'          : {'offset' : 57, 'type': '<48s'}, #array x 3
#}

binblk_tim_transducer_discovery_cmd = {
    'netSvcType'        : {'offset' : 0, 'type': '<B'}, #1
    'netSvcId'          : {'offset' : 1, 'type': '<B'}, #6
    'msgType'           : {'offset' : 2, 'type': '<B'}, #1
    'msgLength'         : {'offset' : 3, 'type': '<H'},
    'ncapId'            : {'offset' : 5, 'type': '<16s'},
    'timId'             : {'offset' : 21, 'type': '<16s'},
    'timeout'           : {'offset' : 37, 'type': '<Q'},
}

#binblk_tim_transducer_discovery_rep = {
#    'netSvcType'        : {'offset' : 0, 'type': '<B'}, #1
#    'netSvcId'          : {'offset' : 1, 'type': '<B'}, #6
#    'msgType'           : {'offset' : 2, 'type': '<B'}, #2
#    'msgLength'         : {'offset' : 3, 'type': '<H'},
#    'errorCode'         : {'offset' : 5, 'type': '<H'},
#    'numOfTransducerChannels'   : {'offset' : 7, 'type': '<2s'}, #num
#    'transducerChannelIds'      : {'offset' : 9, 'type': '<16s'}, #array
#    'transducerChannelNames'    : {'offset' : 25, 'type': '<16s'}, #array
#
#}

binblk_read = {
    'netSvcType'        : {'offset': 0,  'type': '<B'},
    'netSvcID'          : {'offset': 1,  'type': '<B'},
    'msgType'           : {'offset': 2,  'type': '<B'},
    'msgLength'         : {'offset': 3,  'type': '<H'}, # NaN in C
    'appId'             : {'offset': 5,  'type': '<16s'},
    'ncapId'            : {'offset': 21, 'type': '<16s'},
    'timId'             : {'offset': 37, 'type': '<16s'},
    'channelId'         : {'offset': 53, 'type': '<2s'},
    'samplingMode'      : {'offset': 55, 'type': '<B'},
    'timeout'           : {'offset': 56, 'type': '<8B'},
}

#binblk_read = {
#    'netSvcType'        : {'offset': 0,  'type': '<B'},
#    'netSvcID'          : {'offset': 1,  'type': '<B'},
#    'msgType'           : {'offset': 2,  'type': '<B'},
#    'msgLength'         : {'offset': 3,  'type': '<H'}, # NaN in C
#    'errCode'           : {'offset': 5,  'type': '<2s'},
#    'appId'             : {'offset': 7,  'type': '<16s'},
#    'ncapId'            : {'offset': 23, 'type': '<16s'},
#    'timId'             : {'offset': 39, 'type': '<16s'},
#    'channelId'         : {'offset': 55, 'type': '<2s'},
#    'sampleData'        : {'offset': 57, 'type': '<8s'},
#    'timestamp'         : {'offset': 65, 'type': '<2s'},
#}

binblk_write = {
    'netSvcType'        : {'offset': 0,  'type': '<B'},
    'netSvcID'          : {'offset': 1,  'type': '<B'},
    'msgType'           : {'offset': 2,  'type': '<B'},
    'msgLength'         : {'offset': 3,  'type': '<H'}, # NaN in C
    'appId'             : {'offset': 5,  'type': '<16s'},
    'ncapId'            : {'offset': 21, 'type': '<16s'},
    'timId'             : {'offset': 37, 'type': '<16s'},
    'channelId'         : {'offset': 53, 'type': '<2s'},
    'samplingMode'      : {'offset': 55, 'type': '<B'},
    'dataValue'         : {'offset': 56, 'type': '<B'},
    'timeout'           : {'offset': 57, 'type': '<8B'},
}

#binblk_write = {
#    'netSvcType'        : {'offset': 0,  'type': '<B'},
#    'netSvcID'          : {'offset': 1,  'type': '<B'},
#    'msgType'           : {'offset': 2,  'type': '<B'},
#    'msgLength'         : {'offset': 3,  'type': '<H'}, # NaN in C
#    'errCode'           : {'offset': 5,  'type': '<2s'},
#    'appId'             : {'offset': 7,  'type': '<16s'},
#    'ncapId'            : {'offset': 23, 'type': '<16s'},
#    'timId'             : {'offset': 39, 'type': '<16s'},
#    'channelId'         : {'offset': 55, 'type': '<2s'},
#}

binblk_teds = {
    'netSvcType'        : {'offset': 0,  'type': '<B'},
    'netSvcID'          : {'offset': 1,  'type': '<B'},
    'msgType'           : {'offset': 2,  'type': '<B'},
    'msgLength'         : {'offset': 3,  'type': '<H'}, # NaN in C
    'appId'             : {'offset': 5,  'type': '<16s'},
    'ncapId'            : {'offset': 21, 'type': '<16s'},
    'timId'             : {'offset': 37, 'type': '<16s'},
    'channelId'         : {'offset': 53, 'type': '<2s'},
    'tedsAccessCode'    : {'offset': 55, 'type': '<B'},
    'tedsOffset'        : {'offset': 59, 'type': '<4s'},
    'timeout'           : {'offset': 63, 'type': '<8B'},
}

#binblk_teds = {
#    'netSvcType'        : {'offset': 0,  'type': '<B'},
#    'netSvcID'          : {'offset': 1,  'type': '<B'},
#    'msgType'           : {'offset': 2,  'type': '<B'},
#    'msgLength'         : {'offset': 3,  'type': '<H'}, # NaN in C
#    'appId'             : {'offset': 5,  'type': '<16s'},
#    'ncapId'            : {'offset': 21, 'type': '<16s'},
#    'timId'             : {'offset': 37, 'type': '<16s'},
#    'channelId'         : {'offset': 53, 'type': '<2s'},
#    'tedsOffset'        : {'offset': 55, 'type': '<4s'},
#    'TEDS'              : {'offset': 59, 'type': '<8B'},
#}

#Network service message type
#Reserved 0
#Command 1
#Reply 2
#Announcement 3
#Notification 4
#Callback 5

uuid0 = '0x00000000000000000000000000000000'
uuid1 = '0x00000000000000000000000000000001'
uuid2 = '0x00000000000000000000000000000010'
# big endian (MSB first)
buuid0 = bytearray([0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0])
buuid1 = bytearray([0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x1])
buuid2 = bytearray([0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x1, 0x0])
bnull = bytearray([0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]);

# a.to_bytes(2, 'big')  # 2 bytes big endian
# b'\x00\x80'
# a.to_bytes(4, 'little')  # 4 bytes little endian
# b'\x80\x00\x00\x00'
# int.from_bytes(b'\x00\x80', 'big')
# 128
# int.from_bytes(b'\x80\x00\x00\x00', 'little')
# 128
# str -> byte .encode()
# byte -> str .decode()

def s16(value):
    return -(value & 0b1000000000000000) | (value & 0b0111111111111111)

def string_to_16byte_array(a: str) -> bytearray:
    # encode strings to bytearray (supposed to be input simple ASCII/latin-1 (UTF-8 character will be more than 1 byte)
    encoded = a.encode('utf-8')[:16]  # limit less than 16 bytes
    padded = encoded.ljust(16, b'\x00')  # zero padding upto 16 bytes
    return bytearray(padded)

def on_connect(client, userdata, flags, rc):
    print('[CONNECTED {}]'.format(rc))
    mqtt_sub_topics = [(topiccop, 0), (topicd0op, 0), (topicdannorecv, 0), (topiccannorecv, 0)]
    pprint.pprint(mqtt_sub_topics)
    client.subscribe(mqtt_sub_topics)

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection.")

def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Received message '" + str(msg.payload) + "' on topic '" + msg.topic + "' with QoS " + str(msg.qos))

def on_publish(mqttc, obj, mid):
    print("on_pub(mid): "+str(mid))

def on_message(mqttc, obj, msg):
    print("on_msg: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    stopic = msg.topic.split('/')
    msg = str(msg.payload.decode('latin-1'))
#    ts = datetime.today().isoformat()
    ts = datetime.datetime.now()
    bts = temporenc.packb(ts)
    sts = str(ts)
    if stopic[1]+'/' == confdata['tomcop']:
        print("C")
        f = io.StringIO()
        f.write(msg)
        f.seek(0)
        csv_reader = csv.reader(f, skipinitialspace=True)
        rmsg = [row for row in csv_reader]
        f.close()
        pprint.pprint(rmsg)
        for mline in rmsg:
            if mline[0]+mline[1]+mline[2] == '211':
                print('Read Sensor Data COP')
                print('appId', mline[3])
                print('ncapId', mline[4])
                print('timId', mline[5])
                print('channelid', mline[6])
                print('samplingMode', mline[7])
                print('timeout', mline[8])
                chid = int(mline[6])
                if mline[4] == uuid0:
                    if mline[5] == uuid0:
                        print(topiccopres)
                        print('publish: appId as ml 3:', mline[3])
                        print('publish: ncapId as ml 4:', mline[4])
                        print('publish: timId as ml 5:', mline[5])
                        print('publish: chid:', str(chid))
                        print('publish: sampleData:', str(vtemp[chid]))
                        print('publish: sts:', sts)
                        client.publish(topiccopres, '2,1,2,0,'+mline[3]+','+mline[4]+','+mline[5]+','+str(chid)+','+str(vtemp[chid])+','+sts)
                        print("Read TEMP Response")
                    elif mline[5] == uuid1:
                        print(topiccopres)
                        print('publish: appId as ml 4:', mline[3])
                        print('publish: ncapId as ml 5:', mline[4])
                        print('publish: timId as ml 6:', mline[5])
                        print('publish: chid:', str(chid))
                        print('publish: sampleData:', str(vhumid[chid]))
                        print('publish: sts:', sts)
                        client.publish(topiccopres, '2,1,2,0,'+mline[3]+','+mline[4]+','+mline[5]+','+str(chid)+','+str(vhumid[chid])+','+sts)
                        print("Read HUMID")
                    else:
                        print("timId Error:", mline[5])
                else:
                    print("ncapId Error:", mline[4])
            elif mline[0]+mline[1]+mline[2] == '271':
                print('Write Xdcr COP')
                print('appId', mline[3])
                print('ncapId', mline[4])
                print('timId', mline[5])
                print('channelid', mline[6])
                print('samplingMode', mline[7])
                print('VAL', mline[8])
                chid = int(mline[6])
                if mline[4] == uuid0:
                    if mline[5] == uuid2:
                        print('publish: appId as ml 4:', mline[3])
                        print('publish: ncapId as ml 5:', mline[4])
                        print('publish: timId as ml 6:', mline[5])
                        print('publish: chid:', str(chid))
                        print('publish: writeData:', mline[8])
                        print('publish: DutyCycle:', int(mline[8])/25+2.4)
                        print('publish: sts:', sts)
                        if pflag == False:
                            p.ChangeDutyCycle(int(mline[8])/25+2.4)
                            time.sleep(0.4)
                            p.ChangeDutyCycle(0.0)
                            client.publish(topiccopres, '2,7,2,0,'+mline[3]+','+mline[4]+','+mline[5]+','+str(chid))
                            print("Write Servo Response")
                        else:
                            print("++++++++++++ Psuedo Servo:", mline[8]);
                    else:
                        print("timId Error:", mline[5])
                else:
                    print("ncapId Error:", mline[4])
            elif mline[0]+mline[1]+mline[2] == '321':
                print("Read TEDS Data COP")
                print('appId', mline[3])
                print('ncapId', mline[4])
                print('timId', mline[5])
                print('channelid', mline[6])
                print('TedsAccessCode = 4', mline[7])
                print('tedsOffset', mline[8])
                chid = int(mline[6])
                if mline[4] == uuid0:
                    if mline[5] == uuid0:
                        client.publish(topiccopres, '3,2,2,'+mline[3]+','+mline[4]+','+mline[5]+','+mline[6]+','+mline[8]+','+confdata['TEMPTEDS'])
                        print("Read TEMP TEDS")
                    elif mline[5] == uuid1:
                        client.publish(topiccopres, '3,2,2,'+mline[3]+','+mline[4]+','+mline[5]+','+mline[6]+','+mline[8]+','+confdata['HUMIDTEDS'])
                        print("Read HUMID TEDS")
                    elif mline[5] == uuid2:
                        client.publish(topiccopres, '3,2,2,'+mline[3]+','+mline[4]+','+mline[5]+','+mline[6]+','+mline[8]+','+confdata['SERVOTEDS'])
                        print("Read SERVO TEDS")
                    else:
                        print("timId Error:",mline[4])
                else:
                    print("ncapId Error:",mline[3])
    elif stopic[1]+'/' == confdata['tomd0op']:
        print("D0")
        mline = {}
        if msg[0:3].encode() == b'\x01\x04\x01':
            print("Receive Discover")
            for k, v in binblk_discoverty_cmd.items():
                t_offset = v['offset']
                mline[k] = struct.unpack_from(v['type'], msg.encode(), t_offset)[0]
            pprint.pprint(mline)
            print("appId: ", mline['appId'])
            sbp = bytearray([0x1, 0x4, 0x2, 0x0, 0x0, 0x0, 0x0])
            mline['ncapId'] = buuid0
            client.publish(topicd0opres, sbp+mline['appId']+mline['ncapId']+string_to_16byte_array(confdata['loc'])+bytearray([0x1, 10, 1, 1, 1]))
        elif msg[0:3].encode() == b'\x01\x05\x01':
            print("Receive TIM Discover")
            for k, v in binblk_tim_discoverty_cmd.items():
                t_offset = v['offset']
                mline[k] = struct.unpack_from(v['type'], msg.encode(), t_offset)[0]
            pprint.pprint(mline)
            print("appId: ", mline['appId'])
            sbp = bytearray([0x1, 0x5, 0x2, 0x0, 0x0, 0x0, 0x0, 0x3])
            mline['ncapId'] = buuid0
            client.publish(topicd0opres, sbp+uuid0+uuid1+uuid2+string_to_16byte_array('Temp')+string_to_16byte_array('Humid')+string_to_16byte_array('Servo'))
        elif msg[0:3].encode() == b'\x01\x06\x01':
            print("Receive XDCR_CH Discover")
            for k, v in binblk_tim_transducer_discoverty_cmd.items():
                t_offset = v['offset']
                mline[k] = struct.unpack_from(v['type'], msg.encode(), t_offset)[0]
            pprint.pprint(mline)
            print("appId: ", mline['appId'])
            sbp = bytearray([0x1, 0x6, 0x2, 0x0, 0x0, 0x0, 0x0, 0x1])
            mline['ncapId'] = buuid0
            client.publish(topicd0opres, sbp+uuid0+string_to_16byte_array('CH0'))
        elif msg[0:3].encode() == b'\x02\x01\x01':
            print("Receive Sync Read")
            for k, v in binblk_read.items():
                t_offset = v['offset']
                mline[k] = struct.unpack_from(v['type'], msg.encode(), t_offset)[0]
            pprint.pprint(mline)
            if mline['ncapId'] == buuid0:
                print("tmid: ", mline['timId'])
                sbp = bytearray([0x2, 0x1, 0x2, 0x0, 0x0, 0x0, 0x0])
                chid = int.from_bytes(mline['channelId'], 'big')
                print("chid(ml): ", mline['channelId'])
                print('chid:',chid)
                if mline['timId'] == buuid0:
                    client.publish(topicd0opres, sbp+mline['appId']+mline['ncapId']+mline['timId']+bytearray(mline['channelId'])+(str(vtemp[chid]).encode()+bnull)[0:7]+bts)
                    print("Read TEMP")
                elif mline['timId'] == buuid1:
                    client.publish(topicd0opres, sbp+mline['appId']+mline['ncapId']+mline['timId']+bytearray(mline['channelId'])+(str(vhumid[chid]).encode()+bnull)[0:7]+bts)
                    print("Read HUMID")
                else:
                    print("timId Error", mline['timId'])
            else:
                print("ncapId Error")
        elif msg[0:3].encode() == b'\x02\x07\x01':
            print("Receive Sync Write")
            for k, v in binblk_write.items():
                t_offset = v['offset']
                mline[k] = struct.unpack_from(v['type'], msg.encode(), t_offset)[0]
            pprint.pprint(mline)
            if mline['ncapId'] == buuid0:
                print("tmid: ", mline['timId'])
                sbp = bytearray([0x2, 0x7, 0x2, 0x0, 0x0, 0x0, 0x0])
                chid = int.from_bytes(mline['channelId'], 'big')
                print("chid(ml): ", mline['channelId'])
                print('chid:',chid)
                print('dataValue:',mline['dataValue'])
                if mline['timId'] == buuid2:
                    if pflag == False:
                        p.ChangeDutyCycle(int(mline['dataValue'])/25+2.4)
                        time.sleep(0.4)
                        p.ChangeDutyCycle(0.0)
                        client.publish(topicd0opres, sbp+mline['appId']+mline['ncapId']+mline['timId']+bytearray(mline['channelId']))
                        print("Write Servo Response")
                    else:
                        print("++++++++++++ Pseudo Servo:", mline['dataValue']);
                else:
                    print("timId Error", mline['timId'])
            else:
                print("ncapId Error")
        elif msg[0:3].encode() == b'\x03\x02\x01':
            print("Receive TEDS")
            for k, v in binblk_teds.items():
                t_offset = v['offset']
                mline[k] = struct.unpack_from(v['type'], msg.encode(), t_offset)[0]
            pprint.pprint(mline)
            if mline['ncapId'] == buuid0:
                sbp = bytearray([0x3, 0x2, 0x2, 0x0, 0x0, 0x0, 0x0])
                if mline['timId'] == buuid0:
                  client.publish(topicd0opres, sbp+mline['appId']+mline['ncapId']+mline['timId']+bytearray(mline['channelId'])+bytearray(mline['tedsOffset'])+bytearray(confdata['TEMPBINTEDS'].encode()))
                  print("Read TEMP BINARY TEDS")
                elif mline['timId'] == buuid1:
                  client.publish(topicd0opres, sbp+mline['appId']+mline['ncapId']+mline['timId']+bytearray(mline['channelId'])+bytearray(mline['tedsOffset'])+bytearray(confdata['HUMIDBINTEDS'].encode()))
                  print("Read HUMID BINARY TEDS")
                elif mline['timId'] == buuid2:
                  client.publish(topicd0opres, sbp+mline['appId']+mline['ncapId']+mline['timId']+bytearray(mline['channelId'])+bytearray(mline['tedsOffset'])+bytearray(confdata['SERVOBINTEDS'].encode()))
                  print("Read SERVO BINARY TEDS")
                else:
                    print("timId Error", mline['timId'])
            else:
                print("ncapId Error")
                print(mline['ncapId'])
    else:
        print("Type of Message Error")


if __name__ == '__main__':
    print('start')
    if sys.version_info[0] != 3:
        print("Version 3 is required")
    print('MQTT setup')
    node = uuid.getnode()
    mac = uuid.UUID(int=node)
    addr = mac.hex[-12:]
    addrm = addr+'mqtt'
    print(' - Client ID='+addr)
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    if confdata.get('username'):
        client.username_pw_set(confdata['username'], confdata['password'])
        print("AUTH:"+confdata['username']+' '+confdata['password'])
    if confdata.get('mqtttls'):
        client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
        print("TLS ON")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
#    client.enable_bridge_mode()
    client.connect(confdata['mqtthost'], port=int(confdata['mqttport']), keepalive=60)
    client.loop(.1)
    client.loop_start()
    print("D0 Publish To:"+topicdop+str(0)+'/TIME '+topicdop+str(0)+'/TEMP '+topicdop+str(0)+'/HUMID')
    while True:
        if pflag == False:
            instance = dht11.DHT11(pin=15)
        try:
            while True:
                if pflag == False:
                    result = instance.read()
                    if result.is_valid():
                        vtemp[0] = result.temperature
                        vhumid[0] = result.humidity
                        if dflag == True:
                            print("Last valid input: " + str(datetime.datetime.now()))
                            print("Temperature: %-3.1f C" % vtemp[0])
                            print("Humidity: %-3.1f %%" % vhumid[0])
                            client.publish(topicdop+str(0)+'/TIME', str(datetime.datetime.now()))
                            client.publish(topicdop+str(0)+'/TEMP', vtemp[0])
                            client.publish(topicdop+str(0)+'/HUMID', vhumid[0])
                else:
                    vtemp[0] = random.randrange(100,300)/10
                    vhumid[0] = random.randrange(200,700)/10
                    print("Last valid input: " + str(datetime.datetime.now()))
                    print("Temperature: %-3.1f C" % vtemp[0])
                    print("Humidity: %-3.1f %%" % vhumid[0])
                    client.publish(topicdop+str(0)+'/TIME', str(datetime.datetime.now()))
                    client.publish(topicdop+str(0)+'/TEMP', vtemp[0])
                    client.publish(topicdop+str(0)+'/HUMID', vhumid[0])
                    time.sleep(1)
        except KeyboardInterrupt:
            print("Cleanup")
            if pflag == False:
                GPIO.cleanup()
            else:
                sys.exit(0)
