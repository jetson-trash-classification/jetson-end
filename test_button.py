import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library

def button_callback(channel):
    print("Button was pushed!")
    # GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 21 to be an input pin and set initial value to be pulled low (off)

GPIO.cleanup() # Clean up
GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
GPIO.setup(21, GPIO.IN) # Set pin 21 to be an input pin and set initial value to be pulled low (off)
GPIO.add_event_detect(21,GPIO.RISING,callback=button_callback, bouncetime=500) # Setup event on pin 21 rising edge
print(GPIO.input(21))
while True:
    pass

