import time
import RPi.GPIO as GPIO


class Buzzer:

    def __init__(self, pin=13):
        self.pin = pin
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)

    def __repr__(self):
        return 'Buzzer set up on pin {} of the Raspberry Pi board.'.format(self.pin)

    def high(self):
        """Sets the buzzer high."""
        GPIO.output(self.pin, GPIO.HIGH)

    def low(self):
        """Sets the buzzer low."""
        GPIO.output(self.pin, GPIO.LOW)

    def beep(self):
        """
        Short buzzer sound.
        Execution time: 0.1 seconds
        """
        self.high()
        time.sleep(0.1)
        self.low()

    def beep_for(self, number_of_seconds):
        """
        Variable buzzer duration sound.
        Parameters:(number_of_seconds: seconds that the buzzer will emit sound)
        Execution time: number_of_seconds 
        """
        self.high()
        time.sleep(number_of_seconds)
        self.low()

    def beep_exit(self):
        """
        Two short buzzer sounds.
        Execution time: 0.3 seconds
        """
        self.beep()
        time.sleep(0.1)
        self.beep()

    def beep_error(self):
        """
        Short buzzer sound followed by longer buzzer sound.
        Execution time: 1.2 seconds
        """
        self.high()
        time.sleep(0.2)
        self.low()
        time.sleep(0.2)
        self.high()
        time.sleep(0.8)
        self.low()

    def clear(self):
        """Cleans up the GPIO channels."""
        GPIO.cleanup(self.pin)
