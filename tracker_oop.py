#!/usr/bin/env python3

import os
import csv
import glob
import json
import time
import queue
import logging
import threading
import subprocess
from collections import deque

import serial
from serial.tools import list_ports
from geopy.distance import geodesic
from mfrc522 import SimpleMFRC522

from lcd_functions import LCD
from buzzer_functions import Buzzer
from languages import English, Romanian, Hungarian


# Declaring MixIn's for Thread Events and Queues ##############################

class ShutdownMixin:
    shutdown = threading.Event()


class UnexpectedShutdownMixin:
    unexpected_shutdown = threading.Event()


class SignalingMixin:
    start_signal = threading.Event()
    stop_signal = threading.Event()


class IDQueueMixin:
    id_queue = queue.Queue()
    id_database = [780870559455, 142189814135]


class DataQueueMixin:
    data_queue = queue.Queue(maxsize=2)


class UserInterfaceMixin:
    lcd = LCD()
    buzzer = Buzzer()

    ui_event_time_set = threading.Event()
    ui_queue_time_set = queue.Queue()
    ui_event_weak_gps = threading.Event()
    ui_event_enroute = threading.Event()
    ui_queue_distance = queue.Queue()
    ui_event_not_enroute = threading.Event()
    ui_event_start_route = threading.Event()
    ui_event_stop_route = threading.Event()
    ui_event_invalid_card = threading.Event()
    ui_event_wrong_card = threading.Event()
    ui_event_not_found_gps = threading.Event()


# Declaring Worker Threads ####################################################

class RFID(threading.Thread,
           ShutdownMixin,
           UnexpectedShutdownMixin,
           SignalingMixin,
           IDQueueMixin,
           UserInterfaceMixin):
    """Thread that handles RFID card reads and
    signals to the main thread accordingly.
    """
    reader = SimpleMFRC522()

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        id_list = deque(maxlen=2)
        while not self.shutdown.is_set():
            time.sleep(3)
            if self.unexpected_shutdown.is_set():
                id_list.append(self.id_queue.get())
            else:
                id_list.append(self.reader.read_id())  # blocking
                logger.info(f'RC522 Card Read. ID: {id_list[0]}.')
                if len(id_list) == 1:
                    print('Start Route')  # TODO: remove
                    self.ui_event_start_route.set()
                    logger.info('Route started.')
                    self.id_queue.put(id_list[0])
                    self.start_signal.set()
                if not all([_id in self.id_database for _id in id_list]):
                    invalid_card_id = id_list.pop()
                    print('Invalid Card')  # TODO: remove
                    self.ui_event_invalid_card.set()
                    logger.warning(f'RC522: Invalid Card! ID: {invalid_card_id}')
                if len(set(id_list)) == 2:
                    wrong_card_id = id_list.pop()
                    print('Wrong Card')  # TODO: remove
                    self.ui_event_wrong_card.set()
                    logger.warning(f'RC522: Wrong card to end journey! ID: {wrong_card_id}')
                if len(id_list) == 2:
                    id_list.clear()
                    print('Stop Route')  # TODO: remove
                    self.ui_event_stop_route.set()
                    logger.info('Route ended.')
                    self.stop_signal.set()
            time.sleep(3)


class GPS(threading.Thread,
          ShutdownMixin,
          DataQueueMixin,
          UserInterfaceMixin):
    """Thread that gets GPS data and passes
    it to the main thread through a queue.
    """
    ublox_vid = '1546'

    def __init__(self, vid=ublox_vid):
        threading.Thread.__init__(self)
        self.port = self.get_gps_port(vid)

    def run(self):
        while not self.shutdown.is_set():
            try:
                with serial.Serial(self.port) as ser:
                    raw_data = ser.readline()
                    if raw_data[3:6] == b'RMC':
                        self.data_queue.put(self.extract_parameters(raw_data))
                        if self.data_queue.full():
                            self.data_queue.get()
            except IOError:
                print('GPS signal not found.')  # TODO: remove
                logger.warning('GPS signal not found. Waiting for GPS signal...')
                self.ui_event_not_found_gps.set()
                time.sleep(1)
            else:
                self.ui_event_not_found_gps.clear()

    def extract_parameters(self, data):
        """Extract the timestamp, latitude and longitude out of a RMC NMEA bytes object."""
        data = str(data).split(',')
        try:
            lat = round(float(data[3][:2]) + float(data[3][2:]) / 60, 6)
            lon = round(float(data[5][:3]) + float(data[5][3:]) / 60, 6)
            _date = data[9][4:6] + '-' + data[9][2:4] + '-' + data[9][:2]
            _time = data[1][:2] + ':' + data[1][2:4] + ':' + data[1][4:6]
            timestamp = '20' + _date + 'T' + _time + 'Z'
        except ValueError:
            print('Waiting for GPS signal...')  # TODO: remove
            logger.warning('Weak GPS signal! Waiting for stronger signal...')
            self.ui_event_weak_gps.set()
        else:
            self.ui_event_weak_gps.clear()
            return timestamp, lat, lon

    @staticmethod
    def get_gps_port(vid):
        """Return the serial port name of the GPS sensor with the specified vendor ID."""
        comports = [port for port in list_ports.comports()]
        for port in comports:
            if vid in port.hwid:
                return port.device


class UserInterface(threading.Thread,
                    ShutdownMixin,
                    UnexpectedShutdownMixin,
                    UserInterfaceMixin
                    ):

    def __init__(self, language='ro'):
        threading.Thread.__init__(self)
        if language.lower() == 'ro':
            self.lang = Romanian()
        elif language.lower() == 'en':
            self.lang = English()
        elif language.lower() == 'hu':
            self.lang = Hungarian()
        else:
            raise NotImplementedError('Available languages: RO, EN, HU')

    def run(self):
        self.lcd.display(self.lang.msg_s_starting, 1)
        self.lcd.display(self.lang.msg_s_tracker, 2)
        self.buzzer.beep_for(0.5)
        time.sleep(0.5)
        self.lcd.display(self.lang.msg_s_updating_time, 1)
        self.lcd.display(self.lang.msg_s_starting, 2)
        while not self.shutdown.is_set():

            if self.ui_event_not_found_gps.is_set():
                self.buzzer.beep_error()
                self.lcd.display(self.lang.msg_s_error, 1)
                self.lcd.display_scrolling(self.lang.msg_d_connect_gps, 2, num_scrolls=1)
                self.ui_event_not_found_gps.clear()

            if self.ui_event_time_set.is_set():
                timestamp = self.ui_queue_time_set.get()
                self.lcd.display(self.lang.msg_s_gps_time_updated, 2)
                time.sleep(1)
                self.lcd.display_scrolling(timestamp, 2, num_scrolls=2)
                time.sleep(1)
                self.ui_event_time_set.clear()

            if self.ui_event_weak_gps.is_set():
                self.lcd.display(self.lang.msg_s_weak_gps, 1)
                self.buzzer.beep_for(1)
                self.lcd.display_scrolling(self.lang.msg_d_waiting_for_signal, 2, num_scrolls=1)
                self.ui_event_weak_gps.clear()

            if self.unexpected_shutdown.is_set() and not self.ui_event_weak_gps.is_set():
                self.unexpected_shutdown.clear()
                self.lcd.clear()
                self.lcd.display(self.lang.msg_s_wait, 1)
                self.buzzer.beep_error()
                self.lcd.display_scrolling(self.lang.msg_d_unexpected_termination, 2, num_scrolls=1)

            if self.ui_event_not_enroute.is_set():
                self.lcd.display(self.lang.msg_s_inactive_route, 1)
                self.lcd.display(self.lang.msg_s_swipe_to_start, 2)
                time.sleep(1)

            if self.ui_event_start_route.is_set():
                self.lcd.display(self.lang.msg_s_card_read, 1)
                self.lcd.display(self.lang.msg_s_start_route, 2)
                time.sleep(1)
                self.ui_event_start_route.clear()

            if self.ui_event_enroute.is_set():
                try:
                    distance = self.ui_queue_distance.get(block=False)
                except queue.Empty:
                    pass
                else:
                    self.lcd.display(self.lang.msg_s_active_route, 1)
                    self.lcd.display(self.lang.msg_s_distance.format(round(distance / 1000, 2)), 2)
                finally:
                    time.sleep(0.2)

            if self.ui_event_stop_route.is_set():
                self.lcd.display(self.lang.msg_s_end_of_route, 1)
                self.buzzer.beep_exit()
                self.lcd.display(self.lang.msg_s_distance.format(round(distance / 1000, 2)), 2)
                time.sleep(3)
                self.ui_event_stop_route.clear()

            if self.ui_event_invalid_card.is_set():
                self.lcd.clear()
                self.lcd.display(self.lang.msg_s_error, 1)
                self.buzzer.beep_for(1)
                self.lcd.display(self.lang.msg_s_invalid_card, 2)
                time.sleep(1)
                self.ui_event_invalid_card.clear()

            if self.ui_event_wrong_card.is_set():
                self.lcd.clear()
                self.lcd.display(self.lang.msg_s_warning, 1)
                self.buzzer.beep_for(1)
                self.lcd.display(self.lang.msg_s_wrong_card, 2)
                time.sleep(1)
                self.ui_event_wrong_card.clear()


###############################################################################

class Journey(ShutdownMixin,
              UnexpectedShutdownMixin,
              SignalingMixin,
              IDQueueMixin,
              DataQueueMixin,
              UserInterfaceMixin):
    gps_buffer = deque(maxlen=2)
    root_dir = '/home/pi/trackman/GPS-Tracker/'
    gps_logs_dir = root_dir + 'logs/gps_logs/'

    def __init__(self):
        self.user_id = None
        self.route_id = None
        self.total_distance = 0
        self.timestamp, self.lat, self.lon = [None, None, None]
        self.timestamp_start, self.lat_start, self.lon_start = [None, None, None]
        self.timestamp_stop, self.lat_stop, self.lon_stop = [None, None, None]

    def run(self):
        logger.info('Tracker Started.')
        logger.info('Starting GPS Time Update.')
        updated_time = False

        while not self.shutdown.is_set():
            self.route_id = self._init_route_id()
            if not updated_time:
                self._gps_time_update()
                updated_time = True
            if self._check_unexpected_shutdown():
                self._fix_unexpected_shutdown()
                print('Unexpected shutdown detected. '
                      'Rebuilding route parameters.')
            else:
                self.ui_event_not_enroute.set()
                self.start_signal.wait()
                self.ui_event_not_enroute.clear()
                self.user_id = self.id_queue.get()
                self.gps_buffer.append(self.data_queue.get())
                print(self.gps_buffer)
                self.timestamp_start, self.lat_start, self.lon_start = self.gps_buffer[0]

            while not self.stop_signal.is_set():
                print('stop signal: ', self.stop_signal.is_set())
                print('weak gps: ', self.ui_event_weak_gps.is_set())
                self.gps_buffer.append(self.data_queue.get())
                print(self.gps_buffer)
                if not self.ui_event_weak_gps.is_set():
                    self.timestamp, self.lat, self.lon = self.gps_buffer[1]
                    self._log_as_csv()
                    try:
                        gps_data = [data[1:] for data in self.gps_buffer]
                    except TypeError:
                        pass
                    else:
                        self.total_distance = self.calculate_distance(gps_data, self.total_distance)
                        self.ui_event_enroute.set()
                        print('Distance: ', self.total_distance)

            self.ui_event_enroute.clear()
            self.gps_buffer.append(self.data_queue.get())
            self.timestamp_stop, self.lat_stop, self.lon_stop = self.gps_buffer[1]

            self._route_to_json()

            # Cleanup
            self.gps_buffer.clear()
            self.total_distance = 0
            self.route_id = None
            self.start_signal.clear()
            self.stop_signal.clear()

    def _init_route_id(self):
        """Check for the last route ID from the routes
        log file and initializes the new route ID."""
        try:
            with open(self.gps_logs_dir + 'routes.log', 'r') as routes_log:
                last_log = routes_log.readlines()[-1].strip()
                last_route_id = json.loads(last_log)['route_id']
                route_id = last_route_id + 1
        except FileNotFoundError:
            route_id = 1
        return route_id

    def _gps_time_update(self):
        try:
            timestamp = self.data_queue.get()[0]
        except TypeError as e:
            print('eroare:', e)
        else:
            subprocess.call([f'sudo date -s "{timestamp[2:10]} {timestamp[11:-1]}"'], shell=True)
            logger.info(f'System time has been set to: {timestamp}')
            self.ui_event_time_set.set()
            self.ui_queue_time_set.put(f'{timestamp[:10]} {timestamp[11:-1]}')

    def _log_as_csv(self):
        """Create a CSV formatted log unique to each route
        or append route data to an existing route log if an
        unexpected system shutdown had occur.

        CSV Log Format: timestamp,latitude,longitude,distance
        """
        route_filename = f'routes/route_{self.route_id}_{self.user_id}.csv'
        route_log_exists = os.path.isfile(self.gps_logs_dir + route_filename)
        with open(self.gps_logs_dir + route_filename, 'a') as route_log:
            headers = ['Timestamp', 'Latitude', 'Longitude', 'Total_Distance']
            writer = csv.DictWriter(route_log, delimiter=',',
                                    lineterminator='\n',
                                    fieldnames=headers)
            if not route_log_exists:
                writer.writeheader()
            writer.writerow({
                'Timestamp': self.timestamp,
                'Latitude':  self.lat,
                'Longitude': self.lon,
                'Total_Distance': self.total_distance,
            })
            route_log.flush()
            os.fsync(route_log)

    def _check_unexpected_shutdown(self):
        """If the current route ID appears in the name of a file inside
        the routes folder that means an unexpected shutdown had occur.
        """
        routes_dir = self.gps_logs_dir + 'routes/'
        if self.route_id in [int(_.split('_')[1]) for _ in os.listdir(routes_dir)]:
            return True
        else:
            return False

    def _fix_unexpected_shutdown(self):
        """Grab the route parameters from the last logged route."""
        self.unexpected_shutdown.set()
        routes_dir = self.gps_logs_dir + 'routes/'
        self.user_id = int(os.path.basename(
            glob.glob(routes_dir + f'route_{self.route_id}_*')[0]) \
            .split('_')[-1].split('.')[0])
        self.id_queue.put(self.user_id)
        with open(routes_dir + f'route_{self.route_id}_{self.user_id}.csv') as file:
            lines = file.read().splitlines()
            self.total_distance = float(lines[-1].split(',')[-1])
            self.timestamp_start = lines[1].split(',')[0]
            self.lat_start = float(lines[1].split(',')[1])
            self.lon_start = float(lines[1].split(',')[2])

            self.gps_buffer.append([self.timestamp_start,
                                    float(lines[-1].split(',')[1]),
                                    float(lines[-1].split(',')[2])
                                    ])

    def _route_to_json(self):
        """Create a JSON route log and save it to routes.log."""
        route = {'route_id':        self.route_id,
                 'user_id':         self.user_id,
                 'timestamp_start': self.timestamp_start,
                 'lat_start':       self.lat_start,
                 'lon_start':       self.lon_start,
                 'timestamp_stop':  self.timestamp_stop,
                 'lat_stop':        self.lat_stop,
                 'lon_stop':        self.lon_stop,
                 'distance':        self.total_distance
                 }
        with open(self.gps_logs_dir + 'routes.log', 'a') as routes_log:
            routes_log.write(json.dumps(route) + '\n')
            routes_log.flush()
            os.fsync(routes_log)

    def calculate_distance(self, gps_data, total_distance):
        """Return the distance traveled in the current journey.

        Arguments:
            gps_data        --  two GPS coordinates
                                [[lat1, lon1], [lat2, lon2]] (in decimal degrees)
            total_distance  --  previously calculated travel distance (in meters)
        """
        if len(gps_data) == 2:
            d_dist = geodesic(gps_data[0], gps_data[1]).m
            if d_dist > 1:
                total_distance = round(total_distance + d_dist, 2)
                del gps_data[0]
            else:
                del gps_data[1]
                self.ui_queue_distance.put(total_distance)
            return total_distance


if __name__ == '__main__':

    # Logging Configuration ###################################################

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(message)s')
    formatter.datefmt = '%Y-%m-%dT%H:%M:%SZ'
    filename = '/home/pi/trackman/GPS-Tracker/logs/system_logs/tracker.log'
    file_handler = logging.FileHandler(filename=filename)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    ###########################################################################

    ui = UserInterface()
    read = GPS()
    rfid = RFID()
    journey = Journey()

    rfid.start()
    read.start()
    ui.start()
    while not journey.shutdown.is_set():
        journey.run()
    read.join()
    rfid.join()
