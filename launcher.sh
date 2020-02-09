#!/bin/bash
#Script that starts the tracker.py script at boot time

base_dir="/home/pi/trackman/GPS-Tracker"

#Extract speed info from ethtool. If speed is  10 Mb/s, no cable is connected.
#If it is 100 Mb/s, there is a cable present.
# If cable is present, we start only the api (for offline data dump)
# If cable not present, we start only the time_update and the tracker

SPEED=`ethtool eth0 | grep -i "Speed" | awk '{print $2}' | grep -o '[0-9]*'`
if ifconfig | grep -i "eth0" > /dev/null 2>&1; then
    if [ $SPEED == 100 ]; then
        # Ethernet connection OK
        echo "Ethernet OK, starting api"
        sudo python3 $base_dir/api.py &
    else
        # No cable connected
        sudo python3 $base_dir/time_update.py
        sleep 1
        sudo python3 $base_dir/tracker.py &
    fi
fi
