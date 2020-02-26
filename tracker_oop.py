import serial
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

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global shutdown
        id_list = deque(maxlen=2)
        while not shutdown:
            id_list.append(self.reader.read_id())  # blocking
            if len(id_list) == 1:
                print('Start Route')
                self.id_queue.put(id_list[0])
                self.start_signal.release()
            if not all([id in self.id_database for id in id_list]):
                id_list.pop()
                print('Invalid Card')
            if len(set(id_list)) == 2:
                id_list.pop()
                print('Wrong Card')
            if len(id_list) == 2:
                id_list.clear()
                print('Stop Route')
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
        with serial.Serial(self.port) as ser:
            while not shutdown:
                raw_data = ser.readline()
                if raw_data[3:6] == b'RMC':
                    self.data_queue.put(self.extract_parameters(raw_data))
                    if self.data_queue.full():
                        self.data_queue.get()

    @staticmethod
    def extract_parameters(data):
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
            return (timestamp, lat, lon)

    @staticmethod
    def get_gps_port(vid):
        """Gets the serial port on which the GPS sensor is transmitting data."""
        comports = [port for port in list_ports.comports()]
        for port in comports:
            if vid in port.hwid:
                return port.device


class Journey:
    global shutdown
    gps_buffer = deque(maxlen=2)
    request_data_event = threading.Event()

    def __init__(self, id_queue, data_queue, start_signal, stop_signal):
        self.start_signal = start_signal
        self.stop_signal = stop_signal
        self.data_queue = data_queue
        self.id_queue = id_queue
        self.total_distance = 0

    def run(self):
        while not shutdown:
            self.start_signal.acquire()
            self.user_id = self.id_queue.get()
            self.gps_buffer.append(self.data_queue.get())
            self.timestamp_start, self.lat_start, self.lon_start = self.gps_buffer[0]

            while not self.stop_signal.acquire(blocking=False):
                self.gps_buffer.append(self.data_queue.get())
                self.total_distance = self.calculate_distance(self.gps_buffer, self.total_distance)
                print('Distance: ', self.total_distance)

            self.gps_buffer.append(self.data_queue.get())
            self.timestamp_stop, self.lat_stop, self.lon_stop = self.gps_buffer[1]

            print({'user_id':         self.user_id,
                   'timestamp_start': self.timestamp_start,
                   'lat_start':       self.lat_start,
                   'lon_start':       self.lon_start,
                   'timestamp_stop':  self.timestamp_stop,
                   'lat_stop':        self.lat_stop,
                   'lon_stop':        self.lon_stop,
                   'distance':        self.total_distance
                   })

            self.gps_buffer.clear()
            self.total_distance = 0

    @staticmethod
    def calculate_distance(gps_data, total_distance):
        if len(gps_data) == 2:
            d_dist = geodesic(gps_data[0][1:], gps_data[1][1:]).m
            if d_dist > 1:
                total_distance = round(total_distance + d_dist, 2)
                del gps_data[0]
            else:
                del gps_data[1]
            return total_distance


shutdown = False
read = GPS()
rfid = RFID()
journey = Journey(rfid.id_queue, read.data_queue, rfid.start_signal, rfid.stop_signal)

rfid.start()
read.start()
while not shutdown:
    info = journey.run()
    print(info)
read.join()
rfid.join()
