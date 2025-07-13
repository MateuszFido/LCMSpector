"""
Base model class for the LC-Inspector application.

This module provides a base model class that uses the event system for updates.
All model classes should inherit from this base class.
"""

import logging
from model.events import EventEmitter

logger = logging.getLogger(__name__)

class BaseModel(EventEmitter):
    """
    Base class for all model classes in the LC-Inspector application.
    
    This class provides common functionality for all model classes, including
    event emission and logging.
    """
    
    def __init__(self):
        """Initialize the base model with an event emitter."""
        super().__init__()
        logger.info(f"{self.__class__.__name__} initialized.")
