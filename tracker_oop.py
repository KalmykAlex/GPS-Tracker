import serial
import threading
import queue
from mfrc522 import SimpleMFRC522
from geopy.distance import geodesic
from serial.tools import list_ports

import time


class RFID(threading.Thread):
    """Signaling Thread"""
    reader = SimpleMFRC522()
    id_queue = queue.Queue()
    start_event = threading.Event()
    stop_event = threading.Event()

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global shutdown
        while not shutdown:
            _id, info = self.reader.read()
            self.id_queue.put(_id)
            # Set appropriate events depending on state
            if not self.start_event.is_set():
                self.start_event.set()
            elif not self.stop_event.is_set():
                self.stop_event.set()
            else:
                self.start_event.clear()
                self.stop_event.clear()
            time.sleep(5)


class GPS(threading.Thread):
    """Producer Thread"""
    data_queue = queue.Queue()
    ublox_vid = '1546'

    def __init__(self, vid=ublox_vid):
        threading.Thread.__init__(self)
        if vid:
            self.port = self.get_gps_port(vid)

    def run(self):
        global shutdown
        with serial.Serial(self.port) as ser:
            while not shutdown:
                raw_data = ser.readline()
                if raw_data[3:6] == b'RMC':
                    self.extract_parameters(raw_data, self.data_queue)
                    print(self.data_queue.qsize())
                self.data_queue.join()

    @staticmethod
    def extract_parameters(data, data_queue):
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
            data_queue.put([timestamp, lat, lon])

    @staticmethod
    def get_gps_port(vid):
        """Gets the serial port on which the GPS sensor is transmitting data."""
        comports = [port for port in list_ports.comports()]
        for port in comports:
            if vid in port.hwid:
                return port.device


class Journey(threading.Thread):
    """Consumer Thread"""
    global shutdown
    gps_buffer = []

    def __init__(self, id_queue, data_queue, start_event, stop_event):
        threading.Thread.__init__(self)
        start_event.wait()
        self.start = start_event
        self.stop = stop_event
        self.user_id = id_queue.get()
        self.data_queue = data_queue
        self.timestamp_start = None
        self.timestamp_stop = None
        self.lat_start = None
        self.lon_start = None
        self.lat_stop = None
        self.lon_stop = None
        self.total_distance = 0

    def run(self):
        while not shutdown:

            if self.start.is_set():
                self.gps_buffer.append(self.data_queue.get())
                if any([self.timestamp_start, self.lat_start, self.lon_start]) is None:
                    self.timestamp_start = self.gps_buffer[0][0]
                    self.lat_start = self.gps_buffer[0][1]
                    self.lon_start = self.gps_buffer[0][2]
                self.total_distance = self.calculate_distance(self.gps_buffer,
                                                              self.total_distance)
                self.data_queue.task_done()
            elif self.stop.is_set():
                if any([self.timestamp_stop, self.lat_stop, self.lon_stop]) is None:
                    self.timestamp_stop = self.gps_buffer[1][0]
                    self.lat_stop = self.gps_buffer[1][1]
                    self.lon_stop = self.gps_buffer[1][1]
            return {'user_id':         self.user_id,
                    'timestamp_start': self.timestamp_start,
                    'lat_start':       self.lat_start,
                    'lon_start':       self.lon_start,
                    'timestamp_stop':  self.timestamp_stop,
                    'lat_stop':        self.lat_stop,
                    'lon_stop':        self.lon_stop,
                    }

    @staticmethod
    def calculate_distance(gps_data, total_distance):
        if len(gps_data) == 2:
            d_dist = geodesic(gps_data[0][1:], gps_data[1][1:])
            if d_dist > 1:
                total_distance = round(total_distance + d_dist, 2)
                del gps_data[0]
            else:
                del gps_data[1]
        return total_distance


shutdown = False
read = GPS()
rfid = RFID()
journey = Journey(rfid.id_queue, read.data_queue, rfid.start_event, rfid.stop_event)

read.start()
time.sleep(10)
shutdown = True
read.join()
