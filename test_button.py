import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library

def button_callback(channel):
    print("Button was pushed!")
    # GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 23 to be an input pin and set initial value to be pulled low (off)

GPIO.cleanup() # Clean up
GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 23 to be an input pin and set initial value to be pulled low (off)
GPIO.add_event_detect(23,GPIO.FALLING,callback=button_callback) # Setup event on pin 23 rising edge

while True:
    pass

