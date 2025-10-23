"""MQTT communication handler for the cat deterrent system"""

import time
import json
import threading
import paho.mqtt.client as mqtt
import sys
import os

# Add the parent directory to the Python path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_detector.config import Config


class MQTTHandler:  # pylint: disable=too-few-public-methods
    """MQTT handler for communication with MQTT broker with auto-reconnect"""

    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self.connected = False
        self.ping_thread = None
        self._setup_client()
        self._start_connection()
        self._start_ping_thread()

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when client connects to broker"""
        if rc == 0:
            print("✅ MQTT: Successfully connected to broker")
            self.connected = True
        else:
            print(f"❌ MQTT: Connection failed with code {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback when client disconnects from broker"""
        self.connected = False
        if rc != 0:
            print(f"⚠️  MQTT: Unexpected disconnect (code {rc}). Will auto-reconnect...")
        else:
            print("MQTT: Disconnected from broker")

    def _setup_client(self):
        """Sets up the persistent MQTT client with auto-reconnect"""
        self.client = mqtt.Client(client_id=f"katzenschreck_{self.config.camera_name}")
        self.client.username_pw_set(self.config.mqtt_username,
                                   self.config.mqtt_password)
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        # Enable automatic reconnection
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)

    def _start_connection(self):
        """Starts the initial connection to broker"""
        try:
            self.client.connect(self.config.mqtt_broker_url,
                              self.config.mqtt_broker_port, 60)
            # Start network loop in background thread
            self.client.loop_start()
            print(f"🔌 MQTT: Connecting to {self.config.mqtt_broker_url}:{self.config.mqtt_broker_port}...")
        except (mqtt.MQTTException, ConnectionError, OSError) as e:
            print(f"⚠️  MQTT: Initial connection failed: {e}. Will retry automatically...")
            # Start loop anyway - it will keep trying to reconnect
            self.client.loop_start()

    def _start_ping_thread(self):
        """Starts the MQTT ping thread"""
        self.ping_thread = threading.Thread(target=self._mqtt_ping)
        self.ping_thread.daemon = True
        self.ping_thread.start()

    def _mqtt_ping(self):
        """Sends a ping to the MQTT broker every 30 seconds"""
        while True:
            time.sleep(30)
            if self.connected:
                try:
                    extended_topic = f'{self.config.mqtt_topic}/ping'
                    current_timestamp = int(time.time())
                    self.client.publish(extended_topic,
                                      json.dumps({"timestamp": current_timestamp}))
                except Exception as e:
                    print(f"⚠️  MQTT Ping Error: {e}")

    def publish_detection(self, class_name: str, confidence: float,
                         timestamp: str):
        """Sends a detection message to the MQTT broker"""
        if not self.connected:
            print("⚠️  MQTT: Not connected. Message queued for when connection is restored.")
        
        try:
            extended_topic = f'{self.config.mqtt_topic}/{class_name}'
            message = json.dumps({
                "time": timestamp,
                "class": class_name,
                "confidence": confidence
            })
            # QoS 0 for fire and forget (no delivery guarantee)
            result = self.client.publish(extended_topic, message, qos=0)
            
            # Check if message was queued successfully
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                if self.connected:
                    print(f"📤 MQTT: Detection published ({class_name}, {confidence:.2f})")
            else:
                print(f"⚠️  MQTT: Publish failed with code {result.rc}")
                
        except Exception as e:
            print(f"⚠️  MQTT Publish Error: {e}")

    def disconnect(self):
        """Gracefully disconnect from broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            print("MQTT: Disconnected")
