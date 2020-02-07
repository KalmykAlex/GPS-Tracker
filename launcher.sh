#!/bin/sh
#Script that starts the tracker.py script at boot time

sudo python3 /home/pi/trackman/GPS-Tracker/time_update.py
sleep 3
sudo python3 /home/pi/trackman/GPS-Tracker/tracker.py &
sudo python3 /home/pi/trackman/GPS-Tracker/api.py &
