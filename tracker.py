#!/usr/bin/env python3

import serial
import time
import threading
import RPi.GPIO as GPIO

from datetime import date
from queue import Queue
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
    journey_state = False

    card_id_queue = Queue()
    read_card_event = threading.Event()
    read_card_thread = threading.Thread(target=read_card,
                                        args=[read_card_event, card_id_queue],
                                        daemon=True)
    read_card_thread.start()

    while True:
        print('GPS data processing')
        time.sleep(1)

        if read_card_event.is_set():
            print('CARD READ!')
            journey_state = not journey_state
            if not card_id_queue.empty():
                card_id = card_id_queue.get()
                print('Journey State: {}\nLast card ID validated: {}'.format(journey_state,card_id))

