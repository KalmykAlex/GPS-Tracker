import sys
import time
import serial
import logging
import subprocess
from datetime import datetime
from serial.tools import list_ports

# From current directory (lcd.py)
from lcd_functions import Lcd

BASE_DIR = '/home/pi/trackman/GPS-Tracker/'
WAIT_TIME = 3  # seconds

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

    lcd.display('Updating Time', 1)
    lcd.display('Starting...', 2)
    time.sleep(2)
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
                            lcd.display('GPS signal found', 2)
                            time.sleep(2)
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
                            lcd.display_scrolling('Waiting for GPS signal...', 2, num_scrolls=1)
                            logger.warning('GPS Signal weak. Waiting {} '
                                           'second(s) for stronger GPS signal...'.format(WAIT_TIME))
                            time.sleep(WAIT_TIME)  # Waiting for better GPS signal
                            ser.reset_input_buffer()
        except IOError:
            lcd.display_scrolling('Please connect the GPS Sensor', 2, num_scrolls=1)
            logger.warning('GPS Signal not found. Waiting {} second(s) for GPS signal...'.format(WAIT_TIME))
            time.sleep(WAIT_TIME)  # Waiting for GPS signal
        else:
            logger.info('GPS Time update finished successfully.')
            lcd.display_scrolling('Done - GPS Time Update', 2, num_scrolls=1)
            time.sleep(2)
            lcd.display_scrolling('{} 20{} UTC'.format(_time[:5], _date), 2, num_scrolls=2)
            time.sleep(3)
            lcd.clear()
            break
