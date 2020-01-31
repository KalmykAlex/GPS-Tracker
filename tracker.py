#!/usr/bin/env python3

import serial
import time
import logging
import threading
import queue
import RPi.GPIO as GPIO

from geopy.distance import geodesic
from serial.tools import list_ports
from mfrc522 import SimpleMFRC522


def get_gps_port(manufacturer):
    """Gets the serial port on which the GPS sensor is transmitting data."""
    for port in list_ports.comports():
        if manufacturer in port.manufacturer:
            return '/dev/' + port.name


def read_card(event, out_queue):
    """Worker thread used to listen for RFID Card and then set a flag in the main thread"""
    reader = SimpleMFRC522()
    while True:
        try:
            card_id, info = reader.read()
            out_queue.put(card_id)
            logger.info('RC522 Card Read. ID: {} INFO: {}'.format(card_id, info))
            event.set()
            time.sleep(5)
        except Exception as err:
            logger.error(err)


if __name__ == '__main__':

    # Variables initialization
    BASE_DIR = '/home/pi/trackman/GPS-Tracker/'
    journey_state = False
    last_two_coordinates = []
    total_distance = 0
    #TODO: to replace with actual card ID's stored in a postgresql database
    card_db = ['780870559455', '142189814135']

    # GPS COM port configuration
    port = get_gps_port('u-blox')

    # Logging configuration
    logging.basicConfig(filename=BASE_DIR+'logs/tracker.log',
                        format='%(asctime)s: %(levelname)s: %(message)s ',
                        datefmt='%Y-%m-%dT%H:%M:%SZ',
                        level=logging.DEBUG)
    logger = logging.getLogger()

    # Worker Thread, eventing and queue initialization
    card_id_queue = queue.Queue()
    read_card_event = threading.Event()
    read_card_thread = threading.Thread(target=read_card, args=[read_card_event, card_id_queue], daemon=True)
    read_card_thread.start()

    try:
        logger.info('Tracker script started.')
        while True: # to run even if a port disconnect error is raised
            with serial.Serial(port) as ser:
                ser.reset_input_buffer()

                while True:

                    # Read from GPS Sensor and log info
                    gps_raw_data = ser.readline()

                    if gps_raw_data[3:6] == b'RMC':
                        try:
                            gps_data = str(gps_raw_data).split(',')
                            lat = round(float(gps_data[3][:2]) + float(gps_data[3][2:])/60, 6)
                            lon = round(float(gps_data[5][:3]) + float(gps_data[5][3:])/60, 6)
                            _date = '20' + gps_data[9][4:6] + '-' + gps_data[9][2:4] + '-' + gps_data[9][:2]
                            _time = gps_data[1][:2] + ':' + gps_data[1][2:4] + ':' + gps_data[1][4:6]
                            timestamp = _date + 'T' + _time + 'Z'
                        except Exception as err:
                            # TODO: flash red led to indicate weak GPS signal
                            logger.error('Weak GPS signal! Waiting for stronger signal. Python error: {}'.format(err))
                            ser.reset_input_buffer()
                        else:
                            # TODO: turn on green led to indicate good GPS signal
                            # calculate the distance between 2 consecutive coordinates
                            if journey_state:
                                last_two_coordinates.append([lat, lon])
                            else:
                                last_two_coordinates.clear() # clear list when not in journey

                            if len(last_two_coordinates) == 2:
                                delta_distance = geodesic(last_two_coordinates[0], last_two_coordinates[1]).m
                                print(delta_distance)
                                if delta_distance > 1:
                                    total_distance = round(total_distance + delta_distance, 2)
                                del last_two_coordinates[0]

                            # log information in CSV format into a logfile
                            logfile = open(BASE_DIR + 'gps_logs/logdata-{}.log'.format(_date), 'a+')

                            if journey_state:
                                logfile.write('{}, {}, {}, {}\n'.format(timestamp, lat, lon, total_distance))
                            logfile.close()

                            # Verifying correct card validation
                            if read_card_event.is_set():
                                read_card_event.clear()

                                try:
                                    card_id = str(card_id_queue.get(block=False))

                                    if card_id not in card_db:
                                        # TODO: ring buzzer and flash RED LED to indicate invalid card read
                                        logger.warning('RC522: Invalid Card! ID: {}'.format(card_id))
                                        logger.debug('ringing buzzer and flashing red led because card not valid') # TODO: remove after implemented
                                    else:
                                        if not journey_state:
                                            journey_state = True
                                            journey_card = card_id
                                        else:
                                            if journey_card == card_id:
                                                journey_state = False
                                            else:
                                                # TODO: ring buzzer and flash RED LED to indicate invalid card read for end of journey
                                                logger.warning('RC522: Invalid card to end journey! ID: {} and needed ID: {}'.format(card_id, journey_card))
                                                logger.debug('ringing buzzer and flashing red led because needed card {} to end journey'.format(journey_card)) # TODO: remove after implemented

                                    logger.info('Journey State: {}. Last card ID validated: {}'.format(journey_state,card_id))

                                except queue.Empty as err:
                                    logger.error('Card ID queue is empty. Reason: {}'.format(err))
    except IOError as err:
        logger.error(err)
        time.sleep(3) # Waiting 3 seconds for GPS device to reconnect
