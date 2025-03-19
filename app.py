#!/usr/bin/env python3
import os
import subprocess
import threading
import logging
import time
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
socketio = SocketIO(app)

roslaunch_process = None
# New global variables:
forward_output = False      # Controls whether output is forwarded to the client.
streaming_timer = None      # Holds the active timer.

def disable_forwarding():
    """Disable output forwarding after a set period."""
    global forward_output
    forward_output = False
    socketio.emit('log_update', {'data': "\n[Live feed is turned off after 10 seconds.]\n"})

def terminate_process():
    """Terminate the ROS launch process and send final status."""
    global roslaunch_process, forward_output
    if roslaunch_process is not None:
        try:
            roslaunch_process.terminate()
            roslaunch_process.wait()
            roslaunch_process = None
            forward_output = False
            socketio.emit('log_update', {'data': "\n[Recording finished successfully.]\n" + "\n" * 5})
            socketio.emit('status_update', {'status': 'finished recording'})
        except Exception as e:
            logging.error(f"Error terminating process: {str(e)}")

def read_process_output(process):
    """
    Continuously read from the process’s output.
    Lines are forwarded to the website only when forward_output is True.
    """
    for line in iter(process.stdout.readline, ''):
        if line:
            if forward_output:
                socketio.emit('log_update', {'data': line})
        else:
            break
    process.stdout.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_recording():
    global roslaunch_process, forward_output, streaming_timer
    if roslaunch_process is None:
        roslaunch_path = '/opt/ros/noetic/bin/roslaunch'
        bag_name = request.form.get('bag_name', '')
        bag_name_param = f' bag_name:={bag_name}' if bag_name else ''
        command = ['bash', '-c', f'source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && {roslaunch_path} radar_rig_sensor_fusion master.launch record:=true{bag_name_param}']

        try:
            logging.debug(f"Starting command: {command}")
            roslaunch_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            # Enable forwarding immediately.
            forward_output = True
            socketio.emit('status_update', {'status': 'recording'})
            
            # Start a background thread to continuously read output.
            threading.Thread(target=read_process_output, args=(roslaunch_process,), daemon=True).start()
            
            # Set a timer to disable forwarding after 10 seconds.
            if streaming_timer is not None:
                streaming_timer.cancel()
            streaming_timer = threading.Timer(10, disable_forwarding)
            streaming_timer.start()

            return jsonify({'status': 'Recording started successfully.'})
        except Exception as e:
            logging.error(f"Failed to start recording: {str(e)}")
            return jsonify({'status': f'Failed to start recording: {str(e)}'}), 500
    else:
        return jsonify({'status': 'Recording is already running.'}), 400

@app.route('/stop', methods=['POST'])
def stop_recording():
    global roslaunch_process, forward_output, streaming_timer
    if roslaunch_process is not None:
        try:
            # Cancel any current timer (in case we're still in the initial 15-second window)
            if streaming_timer is not None:
                streaming_timer.cancel()
            
            # Re-enable output forwarding for an additional 15 seconds.
            forward_output = True
            
            # Set a new timer that will terminate the process after 1 seconds.
            streaming_timer = threading.Timer(1, terminate_process)
            streaming_timer.start()
            
            # Immediately send a message that the stop command was received.
            socketio.emit('log_update', {'data': "\n[Stop command received, terminating in 1s, forwarding terminal output for max. 15 more seconds.]\n" + "\n" * 5})
            socketio.emit('status_update', {'status': 'stopping recording'})
            return jsonify({'status': 'Stop command received.'})
        except Exception as e:
            return jsonify({'status': f'Failed to stop recording: {str(e)}'}), 500
    else:
        return jsonify({'status': 'No active recording process.'}), 400

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
