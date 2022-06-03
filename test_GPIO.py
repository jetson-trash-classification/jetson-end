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

out_list = [GPIO.LOW, GPIO.LOW, GPIO.LOW, GPIO.LOW]

while 1:
    port = int(input("input pin: "))
    if port > 3 or port < 0:
        pass
    out_list[port] = GPIO.LOW if out_list[port] == GPIO.HIGH else GPIO.HIGH
    for i, pin in enumerate(pin_list):
        GPIO.output(pin, out_list[i])
    print("GPIO output: "+out_list.__str__())     
