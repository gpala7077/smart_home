import json
from datetime import datetime
from threading import Thread

import paho.mqtt.client as mqtt
import pandas as pd

from modules.miscellaneous import Queue


class Mosquitto:
    def __init__(self):
        self.client = mqtt.Client()
        self.db = None
        self.host_ip = None
        self.messages = Queue('FIFO')
        self.interrupts = Queue('LIFO')
        self.commands = None
        self.sensors = pd.DataFrame(columns=['sensor_name', 'sensor_type', 'sensor_value'])
        self.new_status_flag = False

    def mosquitto_callback(self, client, userdata, message):
        """Mosquitto callback function."""

        self.add_message(message)  # Add message to queue
        self.process_message()  # Process message in queue

    def add_message(self, message):
        """Adds message to queue"""

        msg = message.payload.decode("utf-8")  # Decode message
        topic = message.topic  # Get topic
        print('\nReceived message!\n{}\n{}\n'.format(topic, msg))
        self.messages.add((topic, msg))  # Add to queue

        return 'Added message to Queue\n'

    def process_interrupt(self):
        """Process interrupt."""
        data = self.interrupts.get()
        print(self.commands.execute(data))  # Execute command based on the latest interrupt

        timestamp = [datetime.now()] * data.shape[0]  # Add timestamp
        data['history_timestamp'] = timestamp  # Create new column with timestamp
        self.db.replace_insert_data('insert', 'history', data)  # Add data to history table

    def process_message(self):
        """Process Message"""
        topic, msg = self.messages.get()  # Get topic and message

        if 'interrupt' in topic:  # If interrupt
            msg = msg.replace("'", "\"")  # Replace single for double quotes
            msg = json.loads(msg)  # convert string to dictionary
            msg = pd.DataFrame.from_dict(msg)  # Convert dictionary to data frame
            self.interrupts.add(msg)  # Add data frame to interrupt queue
            self.process_interrupt()  # Process interrupt

        elif 'info' in topic:  # If info
            self.new_status_flag = True
            msg = msg.replace("'", "\"")  # Replace single for double quotes
            msg = json.loads(msg)  # convert to dictionary
            self.sensors = pd.DataFrame.from_dict(msg)  # Convert to data frame and replace sensors

        elif 'commands' in topic:  # If command
            self.commands.execute(msg)

    def get_sensors(self):
        """Return sensors data frame"""
        return self.sensors  # Return sensors Data frame

    def new_status(self):
        return self.new_status_flag

    def connect(self):
        """Connect to MQTT Broker and set callback."""

        print('Connecting to broker... {}'.format(self.host_ip))
        self.client.connect(self.host_ip)  # Connect to broker
        self.client.on_message = self.mosquitto_callback  # define callback
        return 'Connected\n'

    def listen(self, channels):
        """Creates a sub-thread and actively listens to given channels."""

        for channel in channels:  # Subscribe to every channel in the list
            print('Listening to... {}'.format(channel))
            self.client.subscribe(channel)

        listen = Thread(target=self.client.loop_forever)  # Begin thread to loop forever.
        listen.start()

        return 'Actively Listening for Mosquitto Broadcasts\n'

    def broadcast(self, channels, payload):
        """Broadcast payload to given channels."""

        for channel in channels:  # Send payload to the list of given channels
            print('\nBroadcasting on...\n{}\nPayload : {}'.format(channel, payload))
            self.client.publish(channel, str(payload))  # publish mosquitto to broker

        return 'Payload sent\n'
