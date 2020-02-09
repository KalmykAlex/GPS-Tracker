#!/bin/bash
#Script that starts the tracker.py script at boot time

base_dir="/home/pi/trackman/GPS-Tracker"

sudo python3 $base_dir/time_update.py 2> $base_dir/logs/system_logs/startup_errors.log
sleep 3
sudo python3 $base_dir/tracker.py & 2> $base_dir/logs/system_logs/startup_errors.log
sudo python3 $base_dir/api.py & > $base_dir/logs/syste_logs/api.log 2> $base_dir/logs/system_logs/startup_errors.log

