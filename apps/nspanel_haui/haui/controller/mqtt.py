import json

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
        
        self.log("=== MQTT Controller __init__() called ===")
        self.log(f"app type: {type(app)}")
        self.log(f"app has 'name' attribute: {hasattr(app, 'name')}")
        if hasattr(app, 'name'):
            self.log(f"app.name: {app.name}")
        else:
            self.log("WARNING: app.name does not exist!")
            # Try to get name from app attributes
            if hasattr(app, '__dict__'):
                self.log(f"app.__dict__ keys: {list(app.__dict__.keys())}")
        self.log(f"config: {config}")
        self.log(f"config type: {type(config)}")
        
        self.mqtt = mqtt
        self.prev_cmd = None
        self._topic_prefix = None
        self._topic_cmd = None
        self._topic_recv = None
        # callback for events
        self._event_callback = event_callback
        
        self.log("=== MQTT Controller __init__() completed ===")

    # part

    def start_part(self):
        """ Starts the part. """
        self.log("=== MQTT Controller start_part() called ===")
        self.log(f"self.app type: {type(self.app)}")
        self.log(f"self.app attributes: {dir(self.app)}")
        
        # Check if self.app.name exists
        if hasattr(self.app, 'name'):
            self.log(f"self.app.name exists: {self.app.name}")
            name = self.app.name
        else:
            self.log("ERROR: self.app.name does not exist!")
            # Fallback to device name
            if hasattr(self.app, 'device') and self.app.device:
                name = self.app.device.get_name()
                self.log(f"Falling back to device name: {name}")
            else:
                name = "nspanel_haui"
                self.log(f"Using default name: {name}")
        
        # topics for communication with panel
        # use AppDaemon instance name (panel name from apps.yaml)
        self.log(f"Using name for topic: {name}")
        self._topic_prefix = f"nspanel_haui/{name}"
        if self._topic_prefix.endswith("/"):
            self._topic_prefix = self._topic_prefix[:-1]
        self._topic_cmd = f"{self._topic_prefix}/cmd"
        self._topic_recv = f"{self._topic_prefix}/recv"
        
        self.log(f"Calculated topic_prefix: {self._topic_prefix}")
        self.log(f"Calculated topic_cmd: {self._topic_cmd}")
        self.log(f"Calculated topic_recv: {self._topic_recv}")
        
        # setup listener
        self.log(f"Subscribing to MQTT topic: {self._topic_recv}")
        try:
            self.mqtt.mqtt_subscribe(topic=self._topic_recv)
            self.log(f"Successfully subscribed to topic: {self._topic_recv}")
        except Exception as e:
            self.log(f"ERROR subscribing to topic {self._topic_recv}: {e}")
        
        self.log(f"Setting up event listener for topic: {self._topic_recv}")
        try:
            self.mqtt.listen_event(
                self.callback_event, "MQTT_MESSAGE", topic=self._topic_recv
            )
            self.log(f"Successfully set up event listener for topic: {self._topic_recv}")
        except Exception as e:
            self.log(f"ERROR setting up event listener: {e}")
        
        self.log("=== MQTT Controller start_part() completed ===")

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
        if data["payload"] == "":
            return
        try:
            event = json.loads(data["payload"])
        except Exception:
            self.log(f"Got invalid json: {data}")
            return
        name = event["name"]
        value = event["value"]
        if name not in ALL_RECV:
            self.log(f"Unknown message {name} received." f" content: {value}")
        # notify about event
        event = HAUIEvent(name, value)
        self._event_callback(event)
