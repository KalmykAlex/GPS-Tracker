[![Generic badge](https://img.shields.io/badge/python_version-3.7-blue.svg)](https://shields.io/)

## Introduction

### About GPS Tracker 

This python project uses a Raspberry Pi 3, an USB GPS Sensor and an RC522 RFID Card Reader in order to log GPS coordinates of specific routes. It's intended usage is for tracking and measuring route distances.

The user uses an RFID Card to start/stop the logging of GPS coordinates, a CSV file is automatically generated that stores the GPS coordinates in a _log format_.

### Equipment List

Below are all the devices and parts that are needed:
- __Raspberry Pi 2 or 3__ (with MicroSD Card and Power Supply)
- __RC522 RFID Reader__ + Card (and wires for connectivity)
- __USB GPS Sensor__ (NMEA Standard Compatible)

Nice to have:
- __LCD Display__ (with I2C interface)
- __Passive Buzzer__ (5V)
- __RGB LED's__ (or normal ones)
- __Power bank__ (to power the raspberry while moving)

### Wiring the system

The __RFID RC522__ has 8 ports and 7 of those we will wire to the Raspberry Pi's GPIO pins as following:
__SDA__ (Serial Data Signal) to __Pin 24__ (GPIO 8), __SCK__ (Serial Clock) to __Pin 23__ (GPIO 11), 
__MOSI__ (Master Out Slave In) to __Pin 19__ (GPIO 10), __MISO__ (Master In Slave Out) to __Pin 21__ (GPIO 9), 
__IRQ__ (Interrupt Request) is left unconnected, __GND__ to __Pin 6__ , __RST__ (Reset-Circuit) to __Pin 22__ (GPIO 25), 
and __3.3V__ (Power In) to __Pin 1__.

The __LCD Display__ connects to the Raspberry via I2C serial connection as follows: __SDA__(Serial Data Signal) to __Pin 3__ (GPIO 2), 
__SCL__ (Serial Clock) to __Pin 5__ (GPIO 3), __VCC__ (5V) to __Pin 2__ and __GND__ to __Pin 9__. 

The __USB GPS Sensor__ will be connected to one of the Raspberry Pi's USB ports. The Raspbian OS will map that USB port
to a file in _/dev/_ folder.

The __Passive Buzzer__ has just 2 wires to be connected: __VCC__ to __Pin 13__(GPIO 27) and
__GND__ to __Pin 14__.

### Setting up the Raspbian

#### Enable serial interfaces (for RC522 and LCD Display)

Before we can run the script we must make sure the Raspberry is setup. First we must make changes to the
configuration. By default the Raspberry Pi has the SPI and I2C interfaces disabled.

    sudo raspi-config
    
In the configuration menu we must chose '5 Interfacing Options' and then 'P4 SPI' for SPI and 'P5 I2C' for I2C, 
press Enter and enable it. After saving the changes you must reboot the Raspberry.
    
    sudo reboot

Once the Raspberry has finished rebooting you can check to make sure the SPI has been enabled by entering the following
commands and to check if __spi_bcm2835__ and __i2c_bcm2835__ is listed.

    lsmod | grep spi
    lsmod | grep i2c

#### Installing spidev and mfrc522 libraries

The following commands will update our Raspberry Pi and install python3-dev and python3-pip.

    sudo apt-get update
    sudo apt-get upgrade
    sudo apt-get install python3-dev python3-pip

After that we must install the spidev and mfrc522 libraries

    sudo pip3 install spidev
    sudo pip3 install mfrc522
    
##### Aditional libraries

We must install aditional libraries that are not part of the standard python libraries package.
These are __pyserial__, a library for serial port communications, __geopy__, a library that will
help us calculate the distance between GPS coordinates and __smbus__ which will be used for the LCD display.

    sudo pip3 install pyserial
    sudo pip3 install geopy
    sudo pip3 install smbus
    
Also, we implemented a REST API used for getting GPS logs from our device with flask. We shall
install the flask library that will then install the necessary dependencies.

    sudo pip3 install flask
    sudo pip3 install flask_restful

### Implementation Details

#### RC.local and Launcher.sh

At boot time a rc.local is configured to stard a _launcher.sh_ script that will in turn start our python
scripts. To setup /etc/rc.local simply add the following line to the end of the file followed by _exit 0_:

    /path/to/bash/script/launcher.sh &
    exit 0
    
Make sure _launcher.sh_ has execute rights and reboot your Raspberry. Now the _launcher.sh_ script
should start automatically.

#### Time Update script - _time_update.py_

After boot, the first python script that we run updates the Raspberry Pi's date and time with information
from the GPS Sensor. If the GPS device is disconnected the script will wait untill the device is reconnected.

#### Tracker script - _tracker.py_

After the Raspberry Pi has updated it's date and time (for logging consistency purposes) we start the
main tracking script. The script was implemented using threads, there is a worker thread that is listening
for RFID Card Readings and signals the Main thread to start logging the GPS data.

#### REST API - _api.py_

A RESTful API developed with flask that provides GPS logs data to GET requests. By default the API works on port 5000.
All the responses are in JSON format.

Requests implemented so far:
- \<HOST IP>:\<PORT>/routes - returns route data for all the logged routes
- \<HOST IP>:\<PORT>/routes?route_id=\<ROUTE_ID> - returns the route data for the specified route
- \<HOST IP>:\<PORT>/routes?user_id=\<USER_ID> - returns route date for all the routes that were made by a specific user

#### Cleanup.sh

This is a bash script that removes all the logs from their locations. This is implemented for testing purposes, to get rid of logs that we don't want and to clean the system.

### Logging

There are a series of logging mechanisms that are implemented. All the files are stored inside _logs_ 
folder in the main project folder:

- __System Logs__: are logs that are generated by:
  - tracker.log - logs information about _tracker.py_ script startup, card redings, journey state, debugging information and 
various errors
  - time_update.log - logs information about _time_update.py_ script startup, successfull date change and various errors
  - startup_errors.log - logs the stderr generated by _tracker.py_, _time_update.py_ and _api.py_ scripts
  - api.log - logs the activity of the REST API.
- __GPS Logs__: are logs that are related to the routes GPS data:
  - routes.log - logs all the routes in JSON format, each new route on a newline.
  - /routes/route_\<routeID>_\<cardID>.csv - logs all the intermediary GPS coordinates in a csv file.

#### GPS logs format

The global routes log, _route.log_ from _gps_logs_ folder logs the data in JSON format as following:

    {"route_id": 1, "timestamp_start": "2020-02-06T13:59:13Z", "lat_start": 44.424587, "lon_start": 26.053704, "user_id":   "142189814135", "timestamp_stop": "2020-02-06T14:01:40Z", "lat_stop": 44.422773, "lon_stop": 26.054524, "distance": 242}
    {"route_id": 2, "timestamp_start": "2020-02-06T14:02:14Z", "lat_start": 44.422534, "lon_start": 26.05434, "user_id": "780870559455", "timestamp_stop": "2020-02-06T14:05:00Z", "lat_stop": 44.424181, "lon_stop": 26.052981, "distance": 233}
    {"route_id": 3, "timestamp_start": "2020-02-06T14:05:17Z", "lat_start": "44.424358", "lon_start": "26.052915", "user_id": "142189814135", "timestamp_stop": "2020-02-06T14:08:53Z", "lat_stop": 44.424475, "lon_stop": 26.053901, "distance": 238}
    ...

The GPS coordinates are saved in a file that is generated automatically in the _gps_logs_ folder inside
the _logs_ folder. It's name is _route_\_\<routeID>_\_\<cardID>.csv_.

The CSV file contains the timestamp, latitude, longitude and total_distance.

    Timestamp               Latitude        Longitude       Total_Distance
    2020-02-06T13:59:14Z	44.424582	26.053711	0
    2020-02-06T13:59:15Z	44.424571	26.053722	1.5
    2020-02-06T13:59:16Z	44.424557	26.053733	3.29
    2020-02-06T13:59:17Z	44.424542	26.05374	5.05
    2020-02-06T13:59:18Z	44.424525	26.053744	6.97
    2020-02-06T13:59:19Z	44.424508	26.053749	8.9
    2020-02-06T13:59:20Z	44.424492	26.053753	10.71
    2020-02-06T13:59:21Z	44.424475	26.053755	12.61
    ...

### Features added

- using a card reader to start/stop the system
- configured logging files for debugging, information and errors
- script that automatically updates system time at startup
- implemented measurement of distance
- system robustness for GPS signal loss
- system robustness for Power Supply loss
- automatically resuming journey after power failure
- multiple cards management (rejection of foreign cards + only one card per route)
- approximation of distance traveled in case of power failure or GPS signal loss
- global routes log that is used for generating route reports
- LCD Display and Buzzer for system feedback
- Rest API for GPS routes
- added support for 3 languages: english, romanian and hungarian

### Features to be added

- implementing a KALMAN filter for better GPS data filtering (requires accelerometer data)
- adding a switch/button to prevent accidental card readings
- adding led indicator for better debugging
- adding a buzzer tone in the case of movement without card readings (as fail-safe)
- database for card users and card id's
- new card registration with master card
- unit tests for the app (with pytest module)
 