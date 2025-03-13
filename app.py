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
streaming_active = False
streaming_ready = threading.Event()

def read_process_output(process):
    global streaming_active
    start_time = time.time()
    streaming_ready.set()  # Signal that streaming is ready

    for line in iter(process.stdout.readline, ''):
        if not streaming_active:
            break
        if line:
            socketio.emit('log_update', {'data': line})
            if time.time() - start_time > 10:
                socketio.emit('log_update', {'data': "\n[Live feed is turned off after 10 seconds.]\n"})
                streaming_active = False
                break
        else:
            break
    process.stdout.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_recording():
    global roslaunch_process, streaming_active
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
            streaming_active = True
            socketio.emit('status_update', {'status': 'recording'})
            
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
    global roslaunch_process, streaming_active
    if roslaunch_process is not None:
        try:
            # Stop the recording directly (no reconnecting logic)
            roslaunch_process.terminate()
            roslaunch_process.wait()
            roslaunch_process = None
            streaming_active = False
            
            # Print "recording finished" message and insert 5 new lines
            socketio.emit('log_update', {'data': "\n[Recording finished successfully.]\n" + "\n" * 5})

            # Send status update if stop is successful
            socketio.emit('status_update', {'status': 'finished recording'})
            return jsonify({'status': 'Recording stopped successfully.'})
        except Exception as e:
            return jsonify({'status': f'Failed to stop recording: {str(e)}'}), 500
    else:
        return jsonify({'status': 'No active recording process.'}), 400



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
