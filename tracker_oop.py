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


# Declaring MixIn's for Thread Events and Queues ##############################

class ShutdownMixin:
    shutdown = threading.Event()


class UnexpectedShutdownMixin:
    unexpected_shutdown = threading.Event()


class SemaphoreMixin:
    start_signal = threading.Semaphore(0)
    stop_signal = threading.Semaphore(0)


class IDQueueMixin:
    id_queue = queue.Queue()
    id_database = [780870559455, 142189814135]


class DataQueueMixin:
    data_queue = queue.Queue(maxsize=2)


# Declaring Worker Threads ####################################################

class RFID(threading.Thread,
           ShutdownMixin,
           UnexpectedShutdownMixin,
           SemaphoreMixin,
           IDQueueMixin):
    """Thread that handles RFID card reads and
    signals to the main thread accordingly.
    """
    reader = SimpleMFRC522()

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        id_list = deque(maxlen=2)
        while not self.shutdown.is_set():
            id_list.append(self.reader.read_id())  # blocking
            logger.info(f'RC522 Card Read. ID: {id_list[0]}.')
            if len(id_list) == 1 and not self.unexpected_shutdown.is_set():
                print('Start Route')  # TODO: remove
                logger.info('Route started.')
                self.id_queue.put(id_list[0])
                self.start_signal.release()
            if not all([_id in self.id_database for _id in id_list]):
                invalid_card_id = id_list.pop()
                print('Invalid Card')  # TODO: remove
                logger.warning(f'RC522: Invalid Card! ID: {invalid_card_id}')
            if len(set(id_list)) == 2:
                wrong_card_id = id_list.pop()
                print('Wrong Card')  # TODO: remove
                logger.warning(f'RC522: Wrong card to end journey! ID: {wrong_card_id}')
            if len(id_list) == 2 or self.unexpected_shutdown.is_set():
                id_list.clear()
                print('Stop Route')  # TODO: remove
                logger.info('Route ended.')
                self.unexpected_shutdown.clear()
                self.stop_signal.release()
            time.sleep(3)


class GPS(threading.Thread,
          ShutdownMixin,
          DataQueueMixin):
    """Thread that gets GPS data and passes
    it to the main thread through a queue.
    """
    ublox_vid = '1546'

    def __init__(self, vid=ublox_vid):
        threading.Thread.__init__(self)
        self.port = self.get_gps_port(vid)

    def run(self):
        try:
            with serial.Serial(self.port) as ser:
                while not self.shutdown.is_set():
                    raw_data = ser.readline()
                    if raw_data[3:6] == b'RMC':
                        self.data_queue.put(self.extract_parameters(raw_data))
                        if self.data_queue.full():
                            self.data_queue.get()
        except IOError:
            print('GPS signal not found.')  # TODO: remove
            logger.warning('GPS signal not found. Waiting for GPS signal...')

    @staticmethod
    def extract_parameters(data):
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
        else:
            return timestamp, lat, lon

    @staticmethod
    def get_gps_port(vid):
        """Return the serial port name of the GPS sensor with the specified vendor ID."""
        comports = [port for port in list_ports.comports()]
        for port in comports:
            if vid in port.hwid:
                return port.device


class Journey(ShutdownMixin,
              UnexpectedShutdownMixin,
              SemaphoreMixin,
              IDQueueMixin,
              DataQueueMixin):
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
        timestamp = self.data_queue.get()[0]
        subprocess.call([f'sudo date -s "{timestamp[2:10]} {timestamp[11:-1]}"'], shell=True)
        logger.info('System time has been set to: {}'.format(timestamp))

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
        self.user_id = os.path.basename(
            glob.glob(routes_dir + f'route_{self.route_id}_*')[0]) \
            .split('_')[-1].split('.')[0]
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

    def run(self):
        logger.info('Tracker Started.')
        logger.info('Starting GPS Time Update.')
        self._gps_time_update()

        while not self.shutdown.is_set():
            self.route_id = self._init_route_id()
            if self._check_unexpected_shutdown():
                self._fix_unexpected_shutdown()
                print('Unexpected shutdown detected. '
                      'Rebuilding route parameters.')
            else:
                self.start_signal.acquire()
                self.user_id = self.id_queue.get()
                self.gps_buffer.append(self.data_queue.get())
                self.timestamp_start, self.lat_start, self.lon_start = self.gps_buffer[0]

            while not self.stop_signal.acquire(blocking=False):
                self.gps_buffer.append(self.data_queue.get())
                self.timestamp, self.lat, self.lon = self.gps_buffer[1]
                self._log_as_csv()
                gps_data = [data[1:] for data in self.gps_buffer]
                self.total_distance = self.calculate_distance(gps_data, self.total_distance)
                print('Distance: ', self.total_distance)

            self.gps_buffer.append(self.data_queue.get())
            self.timestamp_stop, self.lat_stop, self.lon_stop = self.gps_buffer[1]

            self._route_to_json()

            # Cleanup
            self.gps_buffer.clear()
            self.total_distance = 0
            self.route_id = None

    @staticmethod
    def calculate_distance(gps_data, total_distance):
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

    read = GPS()
    rfid = RFID()
    journey = Journey()

    rfid.start()
    read.start()
    while not journey.shutdown.is_set():
        journey.run()
    read.join()
    rfid.join()
