import json
import threading

from ..mapping.const import ALL_RECV, ALL_CMD
from ..abstract.part import HAUIPart
from ..abstract.event import HAUIEvent


class HAUIMQTTController(HAUIPart):

    """ MQTT controller

    Provides access to MQTT functionality.
    """

    def __init__(self, app, config, mqtt, event_callback):
        """ Initialize for MQTT controller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller

            mqtt (): MQTT client
            event_callback (method): Callback for events
        """
        super().__init__(app, config)
        self.mqtt = mqtt
        self.prev_cmd = None
        self._topic_prefix = None
        self._topic_cmd = None
        self._topic_recv = None
        # callback for events
        self._event_callback = event_callback
        # status publishing
        self._status_topic = "nspanel_haui/status"
        self._status_timer = None

    # part

    def start_part(self):
        """ Starts the part. """
        # topics for communication with panel
        # use AppDaemon instance name (panel name from apps.yaml)
        name = self.app.name
        self._topic_prefix = f"nspanel_haui/{name}"
        if self._topic_prefix.endswith("/"):
            self._topic_prefix = self._topic_prefix[:-1]
        self._topic_cmd = f"{self._topic_prefix}/cmd"
        self._topic_recv = f"{self._topic_prefix}/recv"
        self.log(f"Using MQTT topic prefix: {self._topic_prefix}")
        
        # Publish status to let ESPHome device know AppDaemon is available
        # The device subscribes to nspanel_haui/status to detect AppDaemon availability
        self._publish_status("online")
        
        # Republish status every 30 seconds to ensure it stays current
        self._start_status_timer()
        
        # setup listener
        self.mqtt.mqtt_subscribe(topic=self._topic_recv)
        self.mqtt.listen_event(
            self.callback_event, "MQTT_MESSAGE", topic=self._topic_recv
        )
    
    def stop_part(self):
        """ Stops the part. """
        # Stop status timer
        self._stop_status_timer()
        # Publish offline status
        self._publish_status("offline")
    
    def _publish_status(self, status):
        """ Publishes AppDaemon status to MQTT.
        
        Args:
            status (str): Status value ("online" or "offline")
        """
        self.log(f"Publishing AppDaemon status '{status}' to: {self._status_topic}")
        try:
            self.mqtt.mqtt_publish(self._status_topic, status, retain=True)
            self.log(f"Successfully published status '{status}' to {self._status_topic}")
        except Exception as e:
            self.log(f"ERROR publishing status: {e}")
    
    def _start_status_timer(self):
        """ Starts timer to republish status periodically. """
        if self._status_timer is not None:
            return
        self._status_timer = threading.Timer(30.0, self._status_timer_callback)
        self._status_timer.daemon = True
        self._status_timer.start()
    
    def _stop_status_timer(self):
        """ Stops the status timer. """
        if self._status_timer is not None:
            self._status_timer.cancel()
            self._status_timer = None
    
    def _status_timer_callback(self):
        """ Callback for status timer - republishes status. """
        self._publish_status("online")
        # Restart timer
        self._start_status_timer()

    # public

    def send_cmd(self, cmd, value="", force=False):
        """ Sends a command to the panel.

        Args:
            cmd (str): Command
            value (str, optional): Value for command. Defaults to ''.
            force (bool, optional): Force sending the same command.
                Defaults to False.
        """
        if cmd not in ALL_CMD:
            self.log(f"Unknown command {cmd} received." f" content: {value}")
        cmd = json.dumps({"name": cmd, "value": value})
        if not force and self.prev_cmd == cmd:
            self.log(f"Dropping identical consecutive message: {cmd}")
            return
        self.mqtt.mqtt_publish(self._topic_cmd, cmd)
        self.prev_cmd = cmd

    def callback_event(self, event_name, data, kwargs):
        """ Callback for events.

        Args:
            event_name (str): Event name
            data (dict): Event data
            kwargs (dict): Additional arguments
        """
        if event_name != "MQTT_MESSAGE":
            return
        
        # Log all MQTT messages for debugging
        topic = data.get("topic", "unknown")
        payload = data.get("payload", "")
        
        self.log(f"MQTT message received - Topic: {topic}, Payload: {payload[:200]}")  # Limit payload length
        
        if payload == "":
            return
        try:
            event = json.loads(payload)
        except Exception:
            self.log(f"Got invalid json: {data}")
            return
        name = event.get("name", "unknown")
        value = event.get("value", "")
        
        self.log(f"Parsed MQTT event - name: {name}, value: {str(value)[:100]}")
        
        if name not in ALL_RECV:
            self.log(f"Unknown message {name} received." f" content: {value}")
        # notify about event
        event = HAUIEvent(name, value)
        self._event_callback(event)