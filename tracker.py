#!/usr/bin/env python3

import os
import csv
import serial
import time
import json
import glob
import subprocess
import logging
import threading
import queue

from geopy.distance import geodesic
from serial.tools import list_ports
from mfrc522 import SimpleMFRC522

# From current directory(lcd_functions.py and buzzer_functions.py)
from lcd_functions import Lcd
from buzzer_functions import Buzzer

# From current directory (languages.py)
import languages


supported_languages = {'en': 'English', 'ro': 'Romanian', 'hu': 'Hungarian'}
LANGUAGE = 'ro'

# Language select
if supported_languages[LANGUAGE] == 'Romanian':
    lang = languages.Romanian()
elif supported_languages[LANGUAGE] == 'Hungarian':
    lang = languages.Hungarian()
else:
    lang = languages.English()


BASE_DIR = '/home/pi/trackman/GPS-Tracker/'

# Logging configuration
logging.basicConfig(filename=BASE_DIR+'logs/system_logs/tracker.log',
                    format='%(asctime)s: %(levelname)s: %(message)s ',
                    datefmt='%Y-%m-%dT%H:%M:%SZ',
                    level=logging.DEBUG)
logger = logging.getLogger()


def get_gps_port(manufacturer):
    """Gets the serial port on which the GPS sensor is transmitting data."""
    try:
        for com_port in list_ports.comports():
            if manufacturer in com_port.manufacturer:
                return '/dev/' + com_port.name
    except TypeError:
        logger.error('Port for {} device not found.'.format(manufacturer))


def read_card(event, out_queue):
    """Worker thread used to listen for RFID Card and then set a flag in the main thread"""
    reader = SimpleMFRC522()
    while True:
        try:
            _id, info = reader.read()
            out_queue.put(_id)
            print('- Card Read. ID: {} INFO: {}'.format(_id, info if info else 'not filled'))  # TODO: remove
            logger.info('RC522 Card Read. ID: {} INFO: {}'
                        .format(_id, info if info else 'not filled'))
            event.set()
            time.sleep(5)
        except Exception as error:
            logger.error(error)


# Variables initialization
gps_logs_folder = BASE_DIR + 'logs/gps_logs/'
journey_state = False
system_time_set = False
last_two_coordinates = []
total_distance = 0
route = {}
# TODO: to replace with actual card ID's stored in a postgresql database
card_db = ['780870559455', '142189814135']
lcd = Lcd()
buzzer = Buzzer()

# Worker Thread, eventing and queue initialization
card_id_queue = queue.Queue()
read_card_event = threading.Event()
read_card_thread = threading.Thread(target=read_card,
                                    args=[read_card_event, card_id_queue],
                                    daemon=True)

# Display start of execution
print('Tracker script started.')  # TODO: remove
logger.info('Tracker script started.')
lcd.display(lang.msg_s_starting, 1)
lcd.display(lang.msg_s_tracker, 2)
buzzer.beep_for(0.5)
time.sleep(0.5)
logger.info('Starting GPS Time Update.')
lcd.display(lang.msg_s_updating_time, 1)
lcd.display(lang.msg_s_starting, 2)

read_card_thread.start()
while True:  # to run even if a port disconnect error is raised

    # GPS COM port configuration
    port = get_gps_port('u-blox')

    try:
        with serial.Serial(port) as ser:
            ser.reset_input_buffer()

            while True:

                # Read from GPS Sensor and log info
                gps_raw_data = ser.readline()

                if gps_raw_data[3:6] == b'RMC':
                    gps_data = str(gps_raw_data).split(',')
                    try:
                        lat = round(float(gps_data[3][:2]) + float(gps_data[3][2:])/60, 6)
                        lon = round(float(gps_data[5][:3]) + float(gps_data[5][3:])/60, 6)
                        _date = gps_data[9][4:6] + '-' + gps_data[9][2:4] + '-' + gps_data[9][:2]
                        _time = gps_data[1][:2] + ':' + gps_data[1][2:4] + ':' + gps_data[1][4:6]
                        timestamp = '20' + _date + 'T' + _time + 'Z'

                        # Set system time
                        if not system_time_set:
                            subprocess.call(['sudo date -s "{}"'.format(_date + ' '+ _time)], shell=True)
                            logger.info('System time has been set to: {}'.format(timestamp))
                            buzzer.beep()
                            lcd.display(lang.msg_s_updating_time, 1)
                            lcd.display_scrolling(lang.msg_d_gps_time_updated, 2, num_scrolls=1)
                            lcd.display_scrolling(lang.msg_d_timestamp.format(_time[:5], _date), 2, num_scrolls=2)
                            time.sleep(1)
                            system_time_set = True

                    except ValueError:
                        # TODO: flash red led to indicate weak GPS signal
                        lcd.display(lang.msg_s_weak_gps, 1)
                        buzzer.beep_for(0.8)
                        lcd.display_scrolling(lang.msg_d_waiting_for_signal, 2, num_scrolls=1)  #~4.2 sec execution
                        print('Weak GPS signal! Waiting 5 seconds for stronger signal...')  # TODO: remove
                        logger.warning('Weak GPS signal! Waiting 5 seconds for stronger signal...')
                        try:
                            ser.reset_input_buffer()
                        except:
                            # I/O error silencing
                            pass
                    else:
                        # TODO: turn on green led to indicate good GPS signal
                        # calculate the distance between 2 consecutive coordinates
                        if journey_state:
                            last_two_coordinates.append([lat, lon])
                            print(last_two_coordinates)  # TODO: remove
                        else:
                            last_two_coordinates.clear()  # clear list when not in journey

                        if len(last_two_coordinates) == 2:
                            delta_distance = geodesic(last_two_coordinates[0], last_two_coordinates[1]).m
                            # if we are moving (dd>1m) we add to total distance and remove first coord
                            if delta_distance > 1:
                                total_distance = round(total_distance + delta_distance, 2)
                                del last_two_coordinates[0]
                            # if we are stationary (dd<1m) we remove last coord
                            else:
                                del last_two_coordinates[1]

                        # Log route data only if in journey
                        # else check for unexpected script termination
                        if journey_state:
                            routelog_exists = os.path.isfile(gps_logs_folder + 'routes/route_{}_{}.csv'
                                                             .format(route_id, user_id))
                            with open(gps_logs_folder + 'routes/route_{}_{}.csv'.format(route_id, user_id), 'a') as routelog:
                                print('{}, {}, {}, {}'.format(timestamp, lat, lon, total_distance))  # TODO: remove
                                headers = ['Timestamp', 'Latitude', 'Longitude', 'Total_Distance']
                                writer = csv.DictWriter(routelog, delimiter=',',
                                                        lineterminator='\n',
                                                        fieldnames=headers
                                                        )
                                if not routelog_exists:
                                    writer.writeheader()
                                writer.writerow({
                                    'Timestamp': timestamp,
                                    'Latitude': lat,
                                    'Longitude': lon,
                                    'Total_Distance': total_distance
                                })
                                routelog.flush()
                                os.fsync(routelog)

                                # Informs user of journey state and distance
                                lcd.display(lang.msg_s_active_route, 1)
                                lcd.display(lang.msg_s_distance.format(round(total_distance/1000, 2)), 2)

                        else:
                            # Making sure the System is Fail Proof on Power Outage
                            try:
                                with open(gps_logs_folder + 'routes.log', 'r') as global_routelog:
                                    last_routelog = global_routelog.readlines()[-1].strip()
                                    last_route_id = json.loads(last_routelog)['route_id']
                                    route_id = last_route_id + 1
                            except FileNotFoundError:
                                route_id = 1
                            finally:
                                route.update({'route_id': route_id})
                                # TODO: remove following print
                                print('Current route ID: {}'.format(route_id))

                            if route_id in [int(_.split('_')[1]) for _ in os.listdir(gps_logs_folder + 'routes/')]:
                                # TODO: remove following print
                                print(route_id)
                                print('Unexpected Script termination detected. Rebuilding route parameters.')
                                logger.warning('Unexpected Script termination detected. '
                                               'Rebuilding route parameters.')
                                lcd.clear()
                                lcd.display(lang.msg_s_wait, 1)
                                buzzer.beep_error()
                                lcd.display_scrolling(lang.msg_d_unexpected_termination, 2, num_scrolls=1)

                                # Automatically resume the journey of last user_id validated card
                                user_id = os.path.basename(glob.glob(gps_logs_folder + 'routes/route_{}_*'.format(route_id))[0]).split('_')[-1].split('.')[0]
                                journey_state = True

                                # Rebuilding Route Parameters
                                with open(gps_logs_folder + 'routes/route_{}_{}.csv'.format(route_id, user_id)) as file:
                                    lines = file.read().splitlines()
                                    total_distance = float(lines[-1].split(',')[-1])
                                    route.update([
                                        ('timestamp_start', lines[1].split(',')[0]),
                                        ('lat_start', float(lines[1].split(',')[1])),
                                        ('lon_start', float(lines[1].split(',')[2])),
                                    ])
                                    # Resuming Distance Calculation
                                    last_lat = float(lines[-1].split(',')[1])
                                    last_lon = float(lines[-1].split(',')[2])
                                    last_two_coordinates = [[last_lat, last_lon]]

                            else:
                                # Informing user of inactive jouney
                                lcd.display(lang.msg_s_inactive_route, 1)
                                lcd.display(lang.msg_s_swipe_to_start, 2)
                                time.sleep(1)

                        # Verifying correct card validation
                        if read_card_event.is_set():
                            read_card_event.clear()
                            card_id = str(card_id_queue.get(block=False))

                            # LCD display card read event
                            buzzer.beep()
                            lcd.display(lang.msg_s_card_read, 1)
                            lcd.display(lang.msg_s_id.format(card_id), 2)
                            time.sleep(0.9)

                            if card_id not in card_db:
                                # TODO: ring buzzer and flash RED LED to indicate invalid card read
                                print('- Invalid Card Read! ID: {}'.format(card_id))  # TODO: remove
                                lcd.clear()
                                lcd.display(lang.msg_s_error, 1)
                                buzzer.high()
                                lcd.display(lang.msg_s_invalid_card, 2)
                                buzzer.low()
                                logger.warning('RC522: Invalid Card! ID: {}'.format(card_id))
                                # TODO: remove following line after implementation
                                logger.debug('Ringing buzzer and flashing red led because card not valid')
                            else:
                                if not journey_state:
                                    journey_state = True  # beginning of journey
                                    user_id = card_id

                                    # journaling start route parameters
                                    route.update([
                                        ('timestamp_start', timestamp),
                                        ('lat_start', lat),
                                        ('lon_start', lon)
                                    ])

                                else:
                                    if user_id == card_id:
                                        journey_state = False  # ending of journey

                                        # Inform user of journey end
                                        lcd.clear()
                                        lcd.display(lang.msg_s_end_of_route, 1)
                                        buzzer.beep_exit()
                                        lcd.display(lang.msg_s_distance.format(round(total_distance/1000, 2)), 2)
                                        time.sleep(3)

                                        # Stop Route Parameters
                                        route.update([
                                            ('user_id', user_id),
                                            ('timestamp_stop', timestamp),
                                            ('lat_stop', lat),
                                            ('lon_stop', lon),
                                            ('distance', round(total_distance/1000, 2))
                                        ])

                                        total_distance = 0  # resetting total distance at end of journey

                                        # Creating Global Routes Logging File
                                        with open(gps_logs_folder + 'routes.log', 'a') as global_routelog:
                                            global_routelog.write(json.dumps(route) + '\n')
                                            global_routelog.flush()
                                            os.fsync(global_routelog)
                                    else:
                                        # TODO: ring buzzer and flash RED LED to
                                        #  indicate invalid card read for end of journey
                                        print('- Wrong Card Read! ID {}'.format(card_id))  # TODO: remove
                                        logger.warning('RC522: Invalid card to end journey! '
                                                       'ID: {} and needed ID: {}'
                                                       .format(card_id, user_id))
                                        # TODO: remove following line after implementation
                                        logger.debug('Ringing buzzer and flashing red led '
                                                     'because needed card {} to end journey.'
                                                     .format(user_id))
                                        # signaling wrong card to end journey read
                                        lcd.display(lang.msg_s_warning, 1)
                                        buzzer.high()
                                        lcd.display_scrolling(lang.msg_d_wrong_card, 2, num_scrolls=1)
                                        buzzer.low()

                            print('-- Journey State: {}.'.format(journey_state))
                            logger.info('Journey State: {}. '
                                        'Last card ID validated: {}'
                                        .format(journey_state, card_id))

    except IOError as err:
        # TODO: flash red led to indicate lack of GPS sensor
        print(err)  # TODO: remove
        print('GPS signal not found. Waiting 10 seconds for GPS signal...')  # TODO: remove
        buzzer.beep_error()  # 1.2 sec execution
        lcd.display(lang.msg_s_error, 1)
        lcd.display_scrolling(lang.msg_d_connect_gps, 2, num_scrolls=1)  # ~3.2 sec execution
        logger.warning('GPS signal not found. Waiting 10 seconds for GPS signal...')
        time.sleep(5.6)  # Waiting for GPS device to reconnect
