#!/bin/bash
#Script that starts the tracker.py script at boot time

sudo python3 /home/pi/trackman/GPS-Tracker/time_update.py 2> /home/pi/trackman/GPS-Tracker/logs/system_logs/startup_errors.log
sleep 3
sudo python3 /home/pi/trackman/GPS-Tracker/tracker.py & 2> /home/pi/trackman/GPS-Tracker/logs/system_logs/startup_errors.log
sudo python3 /home/pi/trackman/GPS-Tracker/api.py & 2> /home/pi/trackman/GPS-Tracker/logs/system_logs/startup_errors.log
