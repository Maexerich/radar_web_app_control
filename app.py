#!/usr/bin/env python3
import os
import subprocess
import threading
import logging
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
socketio = SocketIO(app)

# Global variable to hold the roslaunch process handle
roslaunch_process = None

def read_process_output(process):
    """Reads stdout from the roslaunch process and emits lines via SocketIO."""
    for line in iter(process.stdout.readline, ''):
        if line:
            socketio.emit('log_update', {'data': line})
        else:
            break
    process.stdout.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_recording():
    global roslaunch_process
    if roslaunch_process is None:
        # Full path to the roslaunch executable
        roslaunch_path = '/opt/ros/noetic/bin/roslaunch'
        bag_name = request.form.get('bag_name', '')  # Get the bag_name from the request, default to an empty string
        bag_name_param = f' bag_name:={bag_name}' if bag_name else ''
        command = ['bash', '-c', f'source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && {roslaunch_path} zadarlabs_arm_ros1 master.launch record:=true{bag_name_param}'] # Extremely 'hacky' but it works!!!
        try:
            logging.debug(f"Starting command: {command}")
            roslaunch_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            # Start a background thread to stream terminal output.
            threading.Thread(target=read_process_output, args=(roslaunch_process,), daemon=True).start()
            return jsonify({'status': 'Recording started successfully.'})
        except Exception as e:
            logging.error(f"Failed to start recording: {str(e)}")
            return jsonify({'status': f'Failed to start recording: {str(e)}'}), 500
    else:
        return jsonify({'status': 'Recording is already running.'}), 400

@app.route('/stop', methods=['POST'])
def stop_recording():
    global roslaunch_process
    if roslaunch_process is not None:
        try:
            roslaunch_process.terminate()
            roslaunch_process = None
            return jsonify({'status': 'Recording stopped successfully.'})
        except Exception as e:
            return jsonify({'status': f'Failed to stop recording: {str(e)}'}), 500
    else:
        return jsonify({'status': 'No active recording process.'}), 400

if __name__ == '__main__':
    # The app will listen on all interfaces on port 5000
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
