import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)  # BOARD pin-numbering scheme
pin_food = 31
pin_residual = 33
pin_hazardous = 35
pin_recyclable = 37
pin_sensor = 29

pin_list = [pin_food, pin_residual, pin_hazardous, pin_recyclable]
GPIO.setup(pin_list, GPIO.OUT)
GPIO.output(pin_list, GPIO.LOW)

while 1:
    port = pin_list[int(input("input pin: "))]
    value = GPIO.LOW if int(input("input value: ")) == 0  else GPIO.HIGH
    GPIO.output(port, value)

