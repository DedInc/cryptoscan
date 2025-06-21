"""
Event System for CryptoScan

Provides async event handling for payment notifications and other events.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Any, Optional, Awaitable
from enum import Enum

from .base import PaymentInfo


class EventType(Enum):
    """Types of events that can be emitted."""
    PAYMENT_DETECTED = "payment_detected"
    PAYMENT_CONFIRMED = "payment_confirmed"
    PAYMENT_FAILED = "payment_failed"
    MONITOR_STARTED = "monitor_started"
    MONITOR_STOPPED = "monitor_stopped"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class PaymentEvent:
    """Event data for payment-related events."""
    
    event_type: EventType
    payment_info: PaymentInfo
    timestamp: datetime
    monitor_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class ErrorEvent:
    """Event data for error events."""
    
    event_type: EventType
    error: Exception
    timestamp: datetime
    monitor_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class MonitorEvent:
    """Event data for monitor lifecycle events."""
    
    event_type: EventType
    timestamp: datetime
    monitor_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


EventCallback = Callable[[Any], Awaitable[None]]


class EventEmitter:
    """
    Async event emitter for handling payment and monitor events.
    
    Supports multiple listeners per event type and async callback execution.
    """
    
    def __init__(self):
        self._listeners: Dict[EventType, List[EventCallback]] = {}
        self._once_listeners: Dict[EventType, List[EventCallback]] = {}
    
    def on(self, event_type: EventType, callback: EventCallback) -> None:
        """
        Register a persistent event listener.
        
        Args:
            event_type: The type of event to listen for
            callback: Async function to call when event occurs
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def once(self, event_type: EventType, callback: EventCallback) -> None:
        """
        Register a one-time event listener.
        
        Args:
            event_type: The type of event to listen for
            callback: Async function to call when event occurs (only once)
        """
        if event_type not in self._once_listeners:
            self._once_listeners[event_type] = []
        self._once_listeners[event_type].append(callback)
    
    def off(self, event_type: EventType, callback: EventCallback) -> bool:
        """
        Remove an event listener.
        
        Args:
            event_type: The type of event
            callback: The callback function to remove
            
        Returns:
            True if callback was found and removed, False otherwise
        """
        removed = False
        
        # Remove from persistent listeners
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
                removed = True
            except ValueError:
                pass
        
        # Remove from once listeners
        if event_type in self._once_listeners:
            try:
                self._once_listeners[event_type].remove(callback)
                removed = True
            except ValueError:
                pass
        
        return removed
    
    async def emit(self, event_type: EventType, event_data: Any) -> None:
        """
        Emit an event to all registered listeners.
        
        Args:
            event_type: The type of event to emit
            event_data: The event data to pass to listeners
        """
        # Collect all callbacks to execute
        callbacks = []
        
        # Add persistent listeners
        if event_type in self._listeners:
            callbacks.extend(self._listeners[event_type])
        
        # Add and remove once listeners
        if event_type in self._once_listeners:
            once_callbacks = self._once_listeners[event_type].copy()
            callbacks.extend(once_callbacks)
            self._once_listeners[event_type].clear()
        
        # Execute all callbacks concurrently
        if callbacks:
            tasks = [callback(event_data) for callback in callbacks]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def listener_count(self, event_type: EventType) -> int:
        """Get the number of listeners for an event type."""
        count = 0
        if event_type in self._listeners:
            count += len(self._listeners[event_type])
        if event_type in self._once_listeners:
            count += len(self._once_listeners[event_type])
        return count
    
    def remove_all_listeners(self, event_type: Optional[EventType] = None) -> None:
        """
        Remove all listeners for a specific event type or all event types.
        
        Args:
            event_type: Specific event type to clear, or None to clear all
        """
        if event_type is None:
            self._listeners.clear()
            self._once_listeners.clear()
        else:
            self._listeners.pop(event_type, None)
            self._once_listeners.pop(event_type, None)
