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
- __Power bank__ (to power the raspberry while moving)

### Wiring the system

The __RFID RC522__ has 8 ports and 7 of those we will wire to the Raspberry Pi's GPIO pins as following:
__SDA__(Serial Data Signal) to __Pin 24__, __SCK__(Serial Clock) to __Pin 23__, __MOSI__(Master Out Slave In) to __Pin 19__,
__MISO__(Master In Slave Out) to __Pin 21__, __IRQ__(Interrupt Request) is left unconnected, __GND__(Ground Power) to __Pin 6__,
__RST__(Reset-Circuit) to __Pin 22__, and __3.3V__(Power In) to __Pin 1__.

The __USB GPS Sensor__ will be connected to one of the Raspberry Pi's USB ports. The Raspbian OS will map that USB port
to a file in _/dev/_ folder.

### Setting up the Raspbian

#### Enable the SPI for RC522

Before we can run the script we must make sure the Raspberry is setup. First we must make changes to the
configuration. By default the Raspberry Pi has the SPI(Serial Peripheral Interface) disabled.

    sudo raspi-config
    
In the configuration menu we must chose '5 Interfacing Options' and then 'P4 SPI', press Enter and enable it.
After saving the changes you must reboot the Raspberry.
    
    sudo reboot

Once the Raspberry has finished rebooting you can check to make sure the SPI has been enabled by entering the following
command and to check if __spi_bcm2835__ is listed.

    lsmod | grep spi

#### Installing spidev and mfrc522 libraries

The following commands will update our Raspberry Pi and install python3-dev and python3-pip.

    sudo apt-get update
    sudo apt-get upgrade
    sudo apt-get install python3-dev python3-pip

After that we must install the spidev and mfrc522 libraries

    sudo pip3 install spidev
    sudo pip3 install mfrc522
    
#### Aditional libraries

We must install aditional libraries that are not part of the standard python libraries package.
These are __pyserial__, a library for serial port communications and __geopy__, a library that will
help us calculate the distance between GPS coordinates.

    sudo pip3 install pyserial
    sudo pip3 install geopy

### Implementation Details

#### Crontab and Launcher.sh

At boot time a crontab is configured to stard a _launcher.sh_ script that will in turn start our python
scripts. To setup the crontab simply type the following commands:

    sudo crontab -e
    
And after the crontab file openes add a line at the bottom:

    #Crontab file
    @reboot sh /path/to/laucher.sh > /path/to/logs/folder/crontab.log 2>&1
    
Make sure _launcher.sh_ has execute rights and reboot your Raspberry. Now the _launcher.sh_ script
should start automatically. Check the _crontab.log_ for possible errors.

#### Time Update script

After boot, the first python script that we run updates the Raspberry Pi's date and time with information
from the GPS Sensor. If the GPS device is disconnected the script will wait untill the device is reconnected.

#### Tracker script

After the Raspberry Pi has updated it's date and time (for logging consistency purposes) we start the
main tracking script. The script was implemented using threads, there is a worker thread that is listening
for RFID Card Readings and signals the Main thread to start logging the GPS data.

There are a series of logging mechanisms that are implemented. All the files are stored inside _logs_ 
folder in the main project folder:
- tracker.log - logs information about _tracker.py_ script startup, card redings, journey state, debugging information and 
various errors
- time_update.log - logs information about _time_update.py_ script startup, successfull date change and various errors
- crontab - logs errors and information about _launcher.sh_ script


### GPS logs format

The GPS coordinates are saved in a file that is generated automatically in the _gps_logs_ folder inside
the project folder. It's name is _logdata-date.log_.

The CSV file contains the timestamp, latitude, longitude and total_distance.

    ...
    2020-01-01T10:30:10Z, 44.121212, 23.345678, 123.12
    2020-01-01T10:30:11Z, 44.121360, 23.345690, 129.12
    ...


### Features added

- using a card reader to start/stop the system
- configured logging files for debugging, information and errors
- script that automatically updates system time at startup
- implemented measurement of distance


### Features to be added

- logging the coordinates in case of failure and automatic reload of the measurement (with some expected errors)
- implementing a KALMAN filter for better GPS data filtering (requires accelerometer data)
- adding a switch/button to prevent accidental card readings
- adding a buzzer/led indicator for better debugging
- adding a buzzer tone in the case of movement without card readings (as fail-safe)
- database for card users and card id's
 
