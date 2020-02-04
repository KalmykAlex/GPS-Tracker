import time
import serial
import logging
import subprocess
from serial.tools import list_ports

BASE_DIR = '/home/pi/trackman/GPS-Tracker/'
WAIT_TIME = 5  # seconds
logging.basicConfig(filename=BASE_DIR+'logs/time_update.log',
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
                            logger.warning('GPS Signal weak. Waiting {} '
                                           'second(s) for stronger GPS signal...'.format(WAIT_TIME))
                            time.sleep(WAIT_TIME)  # Waiting for better GPS signal
        except IOError:
            logger.warning('GPS Signal not found. Waiting {} second(s) for GPS signal...'.format(WAIT_TIME))
            time.sleep(WAIT_TIME)  # Waiting for GPS signal
        else:
            logger.info('GPS Time update finished successfully.')
            break
