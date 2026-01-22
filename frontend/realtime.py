"""
Real-time event system for Vibes Frontend
==========================================

Provides WebSocket and SSE support for instant updates.

WebSocket events:
- board:update - Board state changed
- chat:message - New chat message
- task:moved - Task moved between columns
- agent:status - Agent status changed
- logs:new - New log entries

SSE streams:
- /api/stream/claude - Stream Claude output
- /api/stream/logs - Stream log entries
"""

import json
import queue
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


class EventType(Enum):
    """Event types for the real-time system."""
    BOARD_UPDATE = "board:update"
    CHAT_MESSAGE = "chat:message"
    CHAT_STREAM = "chat:stream"
    CHAT_STREAM_END = "chat:stream:end"
    TASK_CREATED = "task:created"
    TASK_MOVED = "task:moved"
    TASK_DELETED = "task:deleted"
    AGENT_STATUS = "agent:status"
    LOGS_NEW = "logs:new"
    SYSTEM_HEALTH = "system:health"
    CLAUDE_OUTPUT = "claude:output"
    CLAUDE_DONE = "claude:done"
    CLAUDE_ERROR = "claude:error"


@dataclass
class Event:
    """A real-time event."""
    type: EventType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp
        }

    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        return f"event: {self.type.value}\ndata: {json.dumps(self.data)}\n\n"


class EventBus:
    """
    Central event bus for broadcasting real-time updates.

    Supports both WebSocket (via callbacks) and SSE (via queues).
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._sse_queues: Dict[str, queue.Queue] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Subscribe to an event type with a callback."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from an event type."""
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    cb for cb in self._subscribers[event_type] if cb != callback
                ]

    def create_sse_queue(self, client_id: str) -> queue.Queue:
        """Create an SSE queue for a client."""
        with self._lock:
            q = queue.Queue(maxsize=100)
            self._sse_queues[client_id] = q
            return q

    def remove_sse_queue(self, client_id: str):
        """Remove an SSE queue when client disconnects."""
        with self._lock:
            self._sse_queues.pop(client_id, None)

    def emit(self, event: Event):
        """Emit an event to all subscribers and SSE queues."""
        # Notify callback subscribers
        with self._lock:
            callbacks = self._subscribers.get(event.type, []).copy()

        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"[EventBus] Callback error: {e}")

        # Push to SSE queues
        with self._lock:
            queues = list(self._sse_queues.values())

        for q in queues:
            try:
                q.put_nowait(event)
            except queue.Full:
                # Drop oldest event if queue is full
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except:
                    pass

    def emit_typed(self, event_type: EventType, data: Dict[str, Any]):
        """Convenience method to emit an event by type."""
        self.emit(Event(type=event_type, data=data))


# Global event bus instance
event_bus = EventBus()


class SSEStream:
    """
    Server-Sent Events stream generator.

    Usage:
        @app.route('/api/stream/events')
        def stream_events():
            stream = SSEStream(event_bus)
            return Response(
                stream.generate(),
                mimetype='text/event-stream',
                headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
            )
    """

    def __init__(self, bus: EventBus, event_types: Optional[List[EventType]] = None):
        self.bus = bus
        self.event_types = event_types  # Filter by event types, None = all
        self.client_id = f"sse_{time.time()}_{id(self)}"
        self.queue = bus.create_sse_queue(self.client_id)
        self.running = True

    def generate(self):
        """Generator that yields SSE formatted events."""
        try:
            # Send initial connection message
            yield f"event: connected\ndata: {json.dumps({'client_id': self.client_id})}\n\n"

            while self.running:
                try:
                    # Wait for event with timeout for heartbeat
                    event = self.queue.get(timeout=15)

                    # Filter by event type if specified
                    if self.event_types and event.type not in self.event_types:
                        continue

                    yield event.to_sse()

                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat {datetime.now().isoformat()}\n\n"

        except GeneratorExit:
            pass
        finally:
            self.running = False
            self.bus.remove_sse_queue(self.client_id)

    def stop(self):
        """Stop the stream."""
        self.running = False


class ClaudeStreamReader:
    """
    Streams Claude CLI output in real-time via SSE.

    Wraps subprocess execution and emits output line by line.
    """

    def __init__(self, bus: EventBus):
        self.bus = bus
        self.process = None
        self._stop_event = threading.Event()

    def stream_command(self, cmd: str, cwd: str, env: dict):
        """
        Execute command and stream output via event bus.

        Returns a generator for SSE streaming.
        """
        import subprocess
        import os

        self._stop_event.clear()

        def generate():
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd,
                    env={**os.environ, **env},
                    shell=True,
                    bufsize=1
                )

                # Stream output
                buffer = ""
                for char in iter(lambda: self.process.stdout.read(1), ''):
                    if self._stop_event.is_set():
                        self.process.kill()
                        yield f"event: {EventType.CLAUDE_ERROR.value}\ndata: {json.dumps({'message': 'Stopped by user'})}\n\n"
                        break

                    buffer += char

                    # Emit on newline or after accumulating content
                    if char == '\n' or len(buffer) > 100:
                        yield f"event: {EventType.CLAUDE_OUTPUT.value}\ndata: {json.dumps({'chunk': buffer})}\n\n"

                        # Also emit to event bus for WebSocket clients
                        self.bus.emit_typed(EventType.CLAUDE_OUTPUT, {'chunk': buffer})
                        buffer = ""

                # Emit remaining buffer
                if buffer:
                    yield f"event: {EventType.CLAUDE_OUTPUT.value}\ndata: {json.dumps({'chunk': buffer})}\n\n"
                    self.bus.emit_typed(EventType.CLAUDE_OUTPUT, {'chunk': buffer})

                self.process.wait()

                # Emit completion
                yield f"event: {EventType.CLAUDE_DONE.value}\ndata: {json.dumps({'returncode': self.process.returncode})}\n\n"
                self.bus.emit_typed(EventType.CLAUDE_DONE, {'returncode': self.process.returncode})

            except Exception as e:
                yield f"event: {EventType.CLAUDE_ERROR.value}\ndata: {json.dumps({'message': str(e)})}\n\n"
                self.bus.emit_typed(EventType.CLAUDE_ERROR, {'message': str(e)})
            finally:
                self.process = None

        return generate()

    def stop(self):
        """Stop the current stream."""
        self._stop_event.set()
        if self.process:
            try:
                self.process.kill()
            except:
                pass


# Utility functions for common event emissions

def emit_board_update(board_data: dict):
    """Emit a board update event."""
    event_bus.emit_typed(EventType.BOARD_UPDATE, board_data)


def emit_chat_message(role: str, content: str, streaming: bool = False):
    """Emit a chat message event."""
    event_bus.emit_typed(
        EventType.CHAT_STREAM if streaming else EventType.CHAT_MESSAGE,
        {'role': role, 'content': content}
    )


def emit_task_event(event_type: EventType, task_id: str, task_data: dict):
    """Emit a task-related event."""
    event_bus.emit_typed(event_type, {'task_id': task_id, **task_data})


def emit_logs(entries: List[dict]):
    """Emit new log entries."""
    event_bus.emit_typed(EventType.LOGS_NEW, {'entries': entries})
