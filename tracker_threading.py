import sys
import math
import serial
import threading
from datetime import date
from serial.tools import list_ports

ID_LENGTH = 10
PI = math.pi


def calculate_distance(lat1, long1, lat2, long2):
    """Computes the distance in meters between two GPS coordinates."""
    earth_radius = 6367782

    d = math.sin((PI * lat1) / 180) * \
        math.sin((PI * lat2) / 180) + \
        math.cos((PI * lat1) / 180) * \
        math.cos((PI * lat2) / 180) * \
        math.cos((PI * long1) / 180 - (PI * long2) / 180)

    return math.acos(d) * earth_radius


def get_gps_port(manufacturer):
    """Gets the serial port on which the GPS sensor is transmitting data."""
    for port in list_ports.comports():
        if manufacturer in port.manufacturer:
            return '/dev/' + port.name


def read_card(event):
    """Worker thread used to listen for RFID Card and then set a flag in the main thread"""
    for card_id in sys.stdin:
        # Basic check of the card_id integrity
        if len(card_id) == ID_LENGTH:
            event.set()
        else:
            print('Read failure! Try again')


if __name__ == '__main__':
    card_read_event = threading.Event()
    card_read_thread = threading.Thread(target=read_card, args=[card_read_event, ])
    card_read_thread.start()

    port = get_gps_port('u-blox')

    with serial.Serial(port) as ser:
        ser.reset_input_buffer()

        # Variables initialization
        journey_state = False
        coords = []
        distance = 0

        while True:
            if card_read_event.is_set():
                journey_state = not journey_state
                card_read_event.clear()

            gps_raw_data = ser.readline()
            if gps_raw_data[3:6] == b'GLL':

                gps_data = str(gps_raw_data).split(',')
                lat = round(float(gps_data[1][:2]) + float(gps_data[1][2:]) / 60, 6)
                lon = round(float(gps_data[3][:3]) + float(gps_data[3][3:]) / 60, 6)


                _date = date.today().isoformat()
                _time = gps_data[5][:2] + ':' + gps_data[5][2:4] + ':' + gps_data[5][4:6]
                timestamp = _date + 'T' + _time + 'Z'

                with open(f'logdata-{_date}.txt', 'a+') as logfile:
                    logfile.write(f'{timestamp} {lat} {lon} {journey_state}\n')
                    print(f'Wrote to file: {timestamp} {lat} {lon} {journey_state}')
