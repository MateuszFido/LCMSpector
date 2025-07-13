"""
Event system for model updates.

This module provides a simple event system for model updates. It allows components
to subscribe to events and be notified when those events occur.
"""

class EventEmitter:
    """
    A simple event emitter that allows subscribers to listen for events.
    
    This class provides methods to register event listeners, remove them,
    and emit events to all registered listeners.
    """
    
    def __init__(self):
        """Initialize an empty dictionary of event listeners."""
        self._listeners = {}
        
    def on(self, event_type, callback):
        """
        Register a callback function to be called when an event of the given type is emitted.
        
        Parameters
        ----------
        event_type : str
            The type of event to listen for.
        callback : callable
            The function to call when the event is emitted.
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        
    def off(self, event_type, callback):
        """
        Remove a callback function from the list of listeners for an event type.
        
        Parameters
        ----------
        event_type : str
            The type of event to remove the listener from.
        callback : callable
            The function to remove from the list of listeners.
        """
        if event_type in self._listeners and callback in self._listeners[event_type]:
            self._listeners[event_type].remove(callback)
            
    def emit(self, event_type, data=None):
        """
        Emit an event of the given type with the given data.
        
        Parameters
        ----------
        event_type : str
            The type of event to emit.
        data : any, optional
            The data to pass to the callback functions.
        """
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                callback(data)
