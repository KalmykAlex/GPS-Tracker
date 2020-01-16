import serial
import math

port = 'COM7'
readCard = True
PI = math.pi


def distance(lat1, long1, lat2, long2):
    earth_radius = 6367782

    d = math.sin((PI * lat1) / 180) * \
        math.sin((PI * lat2) / 180) + \
        math.cos((PI * lat1) / 180) * \
        math.cos((PI * lat2) / 180) * \
        math.cos((PI * long1) / 180 - (PI * long2) / 180)

    return math.acos(d) * earth_radius


with serial.Serial(port) as ser:
    ser.reset_input_buffer()
    coords = []
    dist = 0

    while readCard:
        line = ser.readline()

        if line[3:6] == b'GLL':
            lat_deg = line[7:17]
            lat = round(float(lat_deg[:2]) + float(lat_deg[2:]) / 60, 6)
            # print(f'Latitude: {lat}')

            lon_deg = line[20:31]
            lon = round(float(lon_deg[:3]) + float(lon_deg[3:]) / 60, 6)
            # print(f'Longitude: {lon}')

            coords.append([lat, lon])

            if len(coords) == 2:
                d_dist = distance(coords[0][0], coords[0][1],
                                  coords[1][0], coords[1][1])
                if d_dist > 1:
                    dist += d_dist
                print(coords)
                coords.pop(0)
                print(coords)
                print(d_dist, dist)

# TODO: implement KALMAN filter for GPS noise reduction
