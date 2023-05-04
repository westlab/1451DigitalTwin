import time

#GPIOの初期設定
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

#GPIO4を出力端子設定
GPIO.setup(4, GPIO.OUT)

#GPIO4をPWM設定、周波数は50Hz
p = GPIO.PWM(4, 50)

#Duty Cycle 0%
p.start(0.0)

while True:
    print("input Duty Cyle (2.5 - 12)")
    dc = float(input())

    #DutyCycle dc%
    p.ChangeDutyCycle(dc)

    #最大180°回転を想定し、0.3sec以上待つ
    time.sleep(0.4)

    #回転終了したら一旦DutyCycle0%にする
    p.ChangeDutyCycle(0.0)
