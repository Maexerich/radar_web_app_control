# Website
For the jetson with MAC: 70:66:55:b1:3b:d1 in flynet-an network with IP 10.10.10.241: http://10.10.10.241:5000

Else, use `hostname -I` to find your IP and then locate website at: `http://<ip_address>:5000`.

# Description
Web application to control data recording of radar test rig.
In essence, this repository contains only the Web-Interface to start and stop ROSBAG recordings of the `master.launch` file from the [GitHub ZadarLabs Arm ROS1](https://github.com/Maexerich/zadarlabs_arm_ros1) ROS repository.

As of now, the test rig has:
- ZadarLabs zPrime radar sensor
- Texas Instruments (TI) AWR1843 radar sensor
- a IMU (don't know what type)


For more details please refer to: [GitHub ZadarLabs Arm ROS1](https://github.com/Maexerich/zadarlabs_arm_ros1).

# Dependencies
Requires:
```bash	
pip install flask flask-socketio
```

# Usage
## Boot-up Behavior
Should start up automatically during boot-up.
I changed the following on the Jetson:
- Create a file with content given by `radar_control.service` using the command  `sudo nano /etc/systemd/system/radar_control.service`. (the same file exists in this repository for your reference)
- Then enable the service using:
```bash
sudo systemctl daemon-reload
sudo systemctl enable radar_control.service
sudo systemctl start radar_control.service
```

The status can be checked with:
```bash
sudo systemctl status radar_control.service
```

## Regular start-up
Run this at least once
```bash
export FLASK_APP=app.py
export FLASK_ENV=development # Optional, can be changed to production
flask run
```
Then to start-up:
```bash
/usr/bin/python3 /home/radar/Documents/radar_web_app_control/app.py
```	
