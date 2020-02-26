import csv
import os
import serial
import json
import glob
import threading
import queue
from mfrc522 import SimpleMFRC522
from geopy.distance import geodesic
from serial.tools import list_ports
from collections import deque

import time


class RFID(threading.Thread):
    """Signaling Thread"""
    reader = SimpleMFRC522()
    id_queue = queue.Queue()
    start_signal = threading.Semaphore(0)
    stop_signal = threading.Semaphore(0)
    id_database = [780870559455, 142189814135]

    def __init__(self, unexpected_shutdown_event):
        threading.Thread.__init__(self)
        self.unexpected_shutdown = unexpected_shutdown_event

    def run(self):
        global shutdown
        id_list = deque(maxlen=2)
        while not shutdown:
            id_list.append(self.reader.read_id())  # blocking
            if len(id_list) == 1 and not self.unexpected_shutdown.is_set():
                print('Start Route')
                self.id_queue.put(id_list[0])
                self.start_signal.release()
            if not all([_id in self.id_database for _id in id_list]):
                id_list.pop()
                print('Invalid Card')
            if len(set(id_list)) == 2:
                id_list.pop()
                print('Wrong Card')
            if len(id_list) == 2 or self.unexpected_shutdown.is_set():
                id_list.clear()
                print('Stop Route')
                self.unexpected_shutdown.clear()
                self.stop_signal.release()
            time.sleep(3)


class GPS(threading.Thread):
    """Producer Thread"""
    data_queue = queue.Queue(maxsize=2)
    ublox_vid = '1546'

    def __init__(self, vid=ublox_vid):
        threading.Thread.__init__(self)
        self.port = self.get_gps_port(vid)

    def run(self):
        global shutdown
        try:
            with serial.Serial(self.port) as ser:
                while not shutdown:
                    raw_data = ser.readline()
                    if raw_data[3:6] == b'RMC':
                        self.data_queue.put(self.extract_parameters(raw_data))
                        if self.data_queue.full():
                            self.data_queue.get()
        except IOError:
            print('GPS signal not found.')

    @staticmethod
    def extract_parameters(data):
        """Extracts the timestamp, latitude and longitude out of a RMC NMEA bytes object."""
        data = str(data).split(',')
        try:
            lat = round(float(data[3][:2]) + float(data[3][2:]) / 60, 6)
            lon = round(float(data[5][:3]) + float(data[5][3:]) / 60, 6)
            _date = data[9][4:6] + '-' + data[9][2:4] + '-' + data[9][:2]
            _time = data[1][:2] + ':' + data[1][2:4] + ':' + data[1][4:6]
            timestamp = '20' + _date + 'T' + _time + 'Z'
        except ValueError:
            print('Waiting for GPS signal...')
        else:
            return timestamp, lat, lon

    @staticmethod
    def get_gps_port(vid):
        """Returns the serial port name of the GPS sensor with the specified vendor ID."""
        comports = [port for port in list_ports.comports()]
        for port in comports:
            if vid in port.hwid:
                return port.device


class Journey:
    global shutdown
    gps_buffer = deque(maxlen=2)
    request_data_event = threading.Event()
    root_dir = '/home/pi/trackman/GPS-Tracker/'
    gps_logs_folder = root_dir + 'logs/gps_logs/'

    def __init__(self, id_queue, data_queue, start_signal, stop_signal, unexpected_shutdown_event):
        self.start_signal = start_signal
        self.stop_signal = stop_signal
        self.data_queue = data_queue
        self.id_queue = id_queue
        self.total_distance = 0
        self.user_id = None
        self.timestamp_start, self.lat_start, self.lon_start = [None, None, None]
        self.timestamp_stop, self.lat_stop, self.lon_stop = [None, None, None]
        self.timestamp, self.lat, self.lon = [None, None, None]
        self.unexpected_shutdown = unexpected_shutdown_event

    def __init_route_id(self):
        try:
            with open(self.gps_logs_folder + 'routes.log', 'r') as routes_log:
                last_log = routes_log.readlines()[-1].strip()
                last_route_id = json.loads(last_log)['route_id']
                route_id = last_route_id + 1
        except FileNotFoundError:
            route_id = 1
        return route_id

    def __log_to_csv(self):
        route_filename = f'routes/route_{self.route_id}_{self.user_id}.csv'
        route_log_exists = os.path.isfile(self.gps_logs_folder + route_filename)
        with open(self.gps_logs_folder + route_filename, 'a') as route_log:
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

    def __check_unexpected_shutdown(self):
        routes_folder = self.gps_logs_folder + 'routes/'
        if self.route_id in [int(_.split('_')[1]) for _ in os.listdir(routes_folder)]:
            return True
        else:
            return False

    def __fix_unexpected_shutdown(self):
        self.unexpected_shutdown.set()
        routes_folder = self.gps_logs_folder + 'routes/'
        self.user_id = os.path.basename(
            glob.glob(routes_folder + f'route_{self.route_id}_*')[0]) \
            .split('_')[-1].split('.')[0]
        with open(routes_folder + f'route_{self.route_id}_{self.user_id}.csv') as file:
            lines = file.read().splitlines()
            self.total_distance = float(lines[-1].split(',')[-1])
            self.timestamp_start = lines[1].split(',')[0]
            self.lat_start = float(lines[1].split(',')[1])
            self.lon_start = float(lines[1].split(',')[2])

            self.gps_buffer.append([self.timestamp_start,
                                    float(lines[-1].split(',')[1]),
                                    float(lines[-1].split(',')[2])
                                    ])

    def __route_to_json(self):
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
        with open(self.gps_logs_folder + 'routes.log', 'a') as routes_log:
            routes_log.write(json.dumps(route) + '\n')
            routes_log.flush()
            os.fsync(routes_log)

    def run(self):
        while not shutdown:
            self.route_id = self.__init_route_id()
            if self.__check_unexpected_shutdown():
                self.__fix_unexpected_shutdown()
            else:
                self.start_signal.acquire()
                self.user_id = self.id_queue.get()
                self.gps_buffer.append(self.data_queue.get())
                self.timestamp_start, self.lat_start, self.lon_start = self.gps_buffer[0]

            while not self.stop_signal.acquire(blocking=False):
                self.gps_buffer.append(self.data_queue.get())
                self.timestamp, self.lat, self.lon = self.gps_buffer[1]
                self.__log_to_csv()
                gps_data = [data[1:] for data in self.gps_buffer]
                self.total_distance = self.calculate_distance(gps_data, self.total_distance)
                print('Distance: ', self.total_distance)

            self.gps_buffer.append(self.data_queue.get())
            self.timestamp_stop, self.lat_stop, self.lon_stop = self.gps_buffer[1]

            self.__route_to_json()

            # Cleanup
            self.gps_buffer.clear()
            self.total_distance = 0
            self.route_id = None

    @staticmethod
    def calculate_distance(gps_data, total_distance):
        """Returns the distance traveled in the current journey.

        Arguments:
            gps_data -- two GPS coordinates [[lat1, lon1], [lat2, lon2]] (in decimal degrees)
            total_distance -- previously calculated travel distance (in meters)
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
    root_dir = '/home/pi/trackman/GPS-Tracker/'
    unexpected_shutdown_event = threading.Event()
    shutdown = False
    read = GPS()
    rfid = RFID(unexpected_shutdown_event)
    journey = Journey(rfid.id_queue,
                      read.data_queue,
                      rfid.start_signal,
                      rfid.stop_signal,
                      unexpected_shutdown_event
                      )

    rfid.start()
    read.start()
    while not shutdown:
        journey.run()
    read.join()
    rfid.join()
