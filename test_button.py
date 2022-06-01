import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)  # BOARD pin-numbering scheme
pin_food = 31
pin_residual = 33
pin_hazardous = 35
pin_recyclable = 37
pin_sensor = 29
pin_button = 23

class A:
    def __init__(self):
        self.a = 0
        GPIO.cleanup()
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(pin_button, GPIO.IN)
        GPIO.add_event_detect(pin_button, GPIO.FALLING,bouncetime=500)
        GPIO.add_event_callback(pin_button, lambda x: self.callback())
        print("init done...")

    def callback(self):
        self.a += 1
        print(self.a)

aa = A()  
while True:
    pass