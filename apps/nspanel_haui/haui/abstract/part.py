from .base import HAUIBase


# a part adding start/stop
class HAUIPart(HAUIBase):

    """ A base class for a part of a Home Automation User Interface (HAUI).

    This class provides a starting point for implementing a HAUI part.
    Subclasses should override the start and stop methods to provide specific functionality.
    """

    def __init__(self, app, config=None):
        """ Initialize for HAUIPart.

        Args:
            app (NSPanelHAI): App
            config (dict, optional): Config for part. Defaults to None.
        """
        super().__init__(app, config)
        self._started = False

    def is_started(self) -> bool:
        """Returns if the part is started.

        Returns:
            bool: Is the part started
        """
        return self._started

    def start(self) -> None:
        """Starts the object."""
        self.app.log(f"HAUIPart.start() called for {type(self).__name__}, already started: {self._started}")
        if self._started:
            self.app.log(f"HAUIPart.start() - {type(self).__name__} already started, skipping")
            return
        self._started = True
        self.app.log(f"HAUIPart.start() - calling start_part() for {type(self).__name__}")
        try:
            self.start_part()
            self.app.log(f"HAUIPart.start() - start_part() completed for {type(self).__name__}")
        except Exception as e:
            self.app.log(f"HAUIPart.start() - ERROR in start_part() for {type(self).__name__}: {e}")
            import traceback
            self.app.log(f"HAUIPart.start() - Traceback: {traceback.format_exc()}")
            raise

    def stop(self) -> None:
        """Stops the object."""
        if not self._started:
            return
        self.stop_part()
        self._started = False

    def start_part(self) -> None:
        """Starts the part.

        This method should be overridden by subclasses to provide specific functionality.
        """

    def stop_part(self) -> None:
        """Stops the part.

        This method should be overridden by subclasses to provide specific functionality.
        """
