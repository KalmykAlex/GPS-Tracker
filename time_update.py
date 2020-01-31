import time
import serial
import logging
import subprocess
from serial.tools import list_ports

BASE_DIR = '/home/pi/trackman/GPS-Tracker/'
logging.basicConfig(filename=BASE_DIR+'logs/time_update.log', level=logging.DEBUG)
logger = logging.getLogger()

def get_gps_port(manufacturer):
    """Gets the serial port on which the GPS sensor is transmitting data."""
    try:
        for port in list_ports.comports():
            if manufacturer in port.manufacturer:
                return '/dev/' + port.name
    except TypeError:
        logger.error('Port for {} device not found'.format(manufacturer))


if __name__ == '__main__':
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

                        if data[1] and data[9]: # check to see if gps data is there (signal strong ernough)
                            date = data[9][4:6] + '-' + data[9][2:4] + '-' + data[9][:2]
                            time = data[1][:2] + ':' + data[1][2:4] + ':' + data[1][4:6]
                            timestamp = date + ' ' + time

                            try:
                                subprocess.call(['sudo date -s "{}"'.format(timestamp)], shell=True)
                            except Exception as err:
                                logger.error(err)
                            else:
                                logger.info('System date has been set to: {}'.format(timestamp))
                                break
                        else:
                            logger.warning('GPS Signal weak. Waiting for stronger GPS signal...')
                            time.sleep(1) # Waiting for better GPS signal
        except IOError as err:
            logger.error(err)
            logger.info('GPS Signal not found. Waiting for GPS signal...')
            time.sleep(1) # Waiting for GPS signal
        else:
            logger.info('GPS Time update finished successfully.')
            break
