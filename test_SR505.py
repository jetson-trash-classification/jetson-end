import RPi.GPIO as GPIO
from time import sleep 

GPIO.setmode(GPIO.BOARD)  # BOARD pin-numbering scheme
pin_sensor = 29

GPIO.setup(pin_sensor, GPIO.IN)

while True:
    print("Movement detect..." if GPIO.input(pin_sensor) == GPIO.HIGH else "No movement...")
    sleep(1)