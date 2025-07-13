"""
Model package for the LC-Inspector application.

This package contains all the model classes for the LC-Inspector application.
The model classes are responsible for data management and business logic.
"""

from model.events import EventEmitter
from model.base import BaseModel
from model.model import Model

__all__ = ['EventEmitter', 'BaseModel', 'Model']
