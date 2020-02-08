import sys
import time
import serial
import logging
import subprocess
from datetime import datetime
from serial.tools import list_ports

# From current directory (lcd_functions.py and buzzer_functions.py)
from lcd_functions import Lcd
from buzzer_functions import Buzzer

BASE_DIR = '/home/pi/trackman/GPS-Tracker/'

logging.basicConfig(filename=BASE_DIR+'logs/system_logs/time_update.log',
                    format='%(levelname)s: %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger()

def get_gps_port(manufacturer):
    """Gets the serial port on which the GPS sensor is transmitting data."""
    try:
        for port in list_ports.comports():
            if manufacturer in port.manufacturer:
                return '/dev/' + port.name
    except TypeError:
        logger.error('Port for {} device not found.'.format(manufacturer))


if __name__ == '__main__':

    lcd = Lcd()
    buzzer = Buzzer()

    lcd.display('Updating Time  ', 1)
    lcd.display('Starting...    ', 2)
    buzzer.beep_for(0.5)
    while True:
        logger.info('Starting GPS Time Update.')
        port = get_gps_port('u-blox')

        try:
            with serial.Serial(port) as ser:
                ser.reset_input_buffer()
                while True:
                    raw_data = ser.readline()

                    if raw_data[3:6] == b'RMC':
                        data = str(raw_data).split(',')

                        # check to see if gps data is present (signal strong enough)
                        if data[1] and data[9]:
                            lcd.display('Updating Time   ', 1)
                            lcd.display('GPS signal found', 2)
                            buzzer.beep()
                            time.sleep(0.9)
                            _date = data[9][4:6] + '-' + data[9][2:4] + '-' + data[9][:2]
                            _time = data[1][:2] + ':' + data[1][2:4] + ':' + data[1][4:6]
                            timestamp = _date + ' ' + _time

                            try:
                                subprocess.call(['sudo date -s "{}"'.format(timestamp)], shell=True)
                            except Exception as err:
                                logger.error(err)
                            else:
                                logger.info('System time has been set to: {}'.format(timestamp))
                                break
                        else:
                            time.sleep(0.3)
                            buzzer.beep_error()  #1.2 sec execution
                            lcd.display('Updating Time   ', 1)
                            lcd.display_scrolling('Waiting for GPS signal...', 2, num_scrolls=1)  #3.2 sec execution
                            time.sleep(0.3)  # to make the total wait time 5 seconds
                            logger.warning('GPS Signal weak. Waiting 5 '
                                           'seconds for stronger GPS signal...')
                            try:
                                ser.reset_input_buffer()
                            except:
                                # I/O error silencing
                                pass
        except IOError:
            time.sleep(2)
            buzzer.beep_error()  # 1.2 sec execution
            time.sleep(1)
            lcd.display('GPS signal loss ', 1)
            lcd.display_scrolling('Please connect the GPS Sensor', 2, num_scrolls=1)  # 4 sec execution
            logger.warning('GPS Signal not found. Waiting 10 seconds for GPS signal...')
            time.sleep(1.8)  # to make the total wait time 10 seconds
        else:
            logger.info('GPS Time update finished successfully.')
            buzzer.beep()
            lcd.display_scrolling('Done - GPS Time Updated', 2, num_scrolls=1)
            lcd.display_scrolling('{} 20{} UTC'.format(_time[:5], _date), 2, num_scrolls=2)
            time.sleep(2)

            buzzer.beep_exit()

            # clean GPIO before exiting
            lcd.clear()
            buzzer.clear()
            break
