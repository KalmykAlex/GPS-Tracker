[![Generic badge](https://img.shields.io/badge/python_version-3.7-blue.svg)](https://shields.io/)

# GPS Tracker 

Calculate the distance driven using Python.
Implemented using Raspberry 3 and USB GPS Sensor.

### Algorithm description

1. Read serial data from the GPS Sensor on the serial link using pyserial module.
2. Parse the information in NMEA format and extract the _Latitude_ and _Longitude_.
3. Calculate the distance between two consecutive points
4. Keep adding the distance between consecutive points to the total distance

### Further additions

- using a card reader to start/stop the system
- logging the coordinates in case of failure and automatic reload of the measurement (with some expected errors)
- implementing a KALMAN filter for better GPS data filtering (requires accelerometer data)
- adding a switch/button to prevent accidental card readings
- adding a buzzer/led indicator for better debugging
- adding a buzzer tone in the case of movement without card readings (as fail-safe)
 