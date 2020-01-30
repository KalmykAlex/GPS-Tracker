#!/usr/bin/env python3

import serial
import time
import threading
import queue
import RPi.GPIO as GPIO

from datetime import date
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
            event.set()
            time.sleep(5)
        except Exception as err:
            # TODO: log exception
            GPIO.cleanup()


if __name__ == '__main__':

    port = get_gps_port('u-blox')
    card_id_queue = queue.Queue()
    read_card_event = threading.Event()
    read_card_thread = threading.Thread(target=read_card,
                                        args=[read_card_event, card_id_queue],
                                        daemon=True)
    read_card_thread.start()


    with serial.Serial(port) as ser:
        ser.reset_input_buffer()

        # Variables initialization
        BASE_DIR = '/home/pi/trackman/GPS-Tracker'
        journey_state = False
        #TODO: to replace with actual card ID's stored in a postgresql database
        card_db = ['780870559455', '142189814135']

        while True:

            # Read from GPS Sensor and log info
            gps_raw_data = ser.readline()
            if gps_raw_data[3:6] == b'GLL':
                try:
                    gps_data = str(gps_raw_data).split(',')
                    lat = round(float(gps_data[1][:2]) + float(gps_data[1][2:])/60, 6)
                    lon = round(float(gps_data[3][:3]) + float(gps_data[3][3:])/60, 6)
                    _date = date.today().isoformat()
                    _time = gps_data[5][:2] + ':' + gps_data[5][2:4] + ':' + gps_data[5][4:6]
                    timestamp = _date + 'T' + _time + 'Z'
                except Exception as err:
                    # TODO: log exception error
                    print(err)
                else:
                    logfile = open(BASE_DIR + '/gps_logs/logdata-{}.log'.format(_date), 'a+')

                    if journey_state:
                        logfile.write('{}, {}, {}\n'.format(timestamp, lat, lon))
                    print('{}, {}, {}, {}'.format(timestamp, lat, lon, journey_state))
                finally:
                    logfile.close()


            # Verifying correct card validation
            if read_card_event.is_set():
                read_card_event.clear()

                try:
                    card_id = str(card_id_queue.get(block=False))

                    if card_id not in card_db:
                        # TODO: ring buzzer and flash RED LED to indicate invalid card read
                        print('EVENT: ringing buzzer and flasing red led because card not valid')
                    else:
                        if not journey_state:
                            journey_state = True
                            journey_card = card_id
                        else:
                            if journey_card == card_id:
                                journey_state = False
                            else:
                                # TODO: ring buzzer and flash RED LED to indicate invalid card read for end of journey
                                print('EVENT: ringing buzzer and flashing red led because needed card {} to end journey'.format(journey_card))

                    print('Journey State: {}. Last card ID validated: {}'.format(journey_state,card_id))

                except queue.Empty:
                    pass
