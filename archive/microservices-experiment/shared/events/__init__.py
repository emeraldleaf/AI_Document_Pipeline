"""Shared event library for event-driven communication between microservices."""

from .publisher import EventPublisher
from .consumer import EventConsumer

__all__ = ['EventPublisher', 'EventConsumer']
