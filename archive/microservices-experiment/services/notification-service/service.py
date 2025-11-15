#!/usr/bin/env python3
"""
Notification Service

Provides WebSocket endpoints for real-time progress updates.
Listens to all document processing events and broadcasts to connected clients.
"""

import os
import sys
import asyncio
import json
from typing import Dict, Set
from datetime import datetime
from loguru import logger

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add shared library to path
sys.path.insert(0, '/app/shared')


# Connection manager for WebSockets
class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        # Map document_id -> set of websockets
        self.document_connections: Dict[str, Set[WebSocket]] = {}
        # Map correlation_id -> set of websockets (for batch tracking)
        self.batch_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, subscription_id: str, subscription_type: str = 'document'):
        """Accept a new WebSocket connection."""
        await websocket.accept()

        if subscription_type == 'document':
            if subscription_id not in self.document_connections:
                self.document_connections[subscription_id] = set()
            self.document_connections[subscription_id].add(websocket)
        elif subscription_type == 'batch':
            if subscription_id not in self.batch_connections:
                self.batch_connections[subscription_id] = set()
            self.batch_connections[subscription_id].add(websocket)

        logger.info(f"Client connected to {subscription_type}/{subscription_id}")

    def disconnect(self, websocket: WebSocket, subscription_id: str, subscription_type: str = 'document'):
        """Remove a WebSocket connection."""
        if subscription_type == 'document':
            if subscription_id in self.document_connections:
                self.document_connections[subscription_id].discard(websocket)
                if not self.document_connections[subscription_id]:
                    del self.document_connections[subscription_id]
        elif subscription_type == 'batch':
            if subscription_id in self.batch_connections:
                self.batch_connections[subscription_id].discard(websocket)
                if not self.batch_connections[subscription_id]:
                    del self.batch_connections[subscription_id]

        logger.info(f"Client disconnected from {subscription_type}/{subscription_id}")

    async def broadcast_to_document(self, document_id: str, message: dict):
        """Broadcast message to all clients subscribed to a document."""
        if document_id not in self.document_connections:
            return

        disconnected = set()
        for websocket in self.document_connections[document_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            self.document_connections[document_id].discard(ws)

    async def broadcast_to_batch(self, correlation_id: str, message: dict):
        """Broadcast message to all clients subscribed to a batch."""
        if correlation_id not in self.batch_connections:
            return

        disconnected = set()
        for websocket in self.batch_connections[correlation_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            self.batch_connections[correlation_id].discard(ws)


# Create FastAPI app
app = FastAPI(title="Notification Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connection manager
manager = ConnectionManager()

# Store for batch progress (correlation_id -> progress data)
batch_progress: Dict[str, Dict] = {}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_document_subscriptions": len(manager.document_connections),
        "active_batch_subscriptions": len(manager.batch_connections),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.websocket("/ws/document/{document_id}")
async def document_websocket(websocket: WebSocket, document_id: str):
    """
    WebSocket endpoint for document-specific progress updates.

    Clients connect to this endpoint to receive real-time updates
    for a specific document as it flows through the pipeline.
    """
    await manager.connect(websocket, document_id, 'document')

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "document_id": document_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Keep connection alive and receive any client messages
        while True:
            data = await websocket.receive_text()
            # Echo back for keepalive
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket, document_id, 'document')
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, document_id, 'document')


@app.websocket("/ws/batch/{correlation_id}")
async def batch_websocket(websocket: WebSocket, correlation_id: str):
    """
    WebSocket endpoint for batch progress updates.

    Clients connect to this endpoint to receive real-time updates
    for an entire batch of documents.
    """
    await manager.connect(websocket, correlation_id, 'batch')

    try:
        # Send initial connection confirmation with current progress
        initial_data = {
            "type": "connected",
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Include current progress if available
        if correlation_id in batch_progress:
            initial_data["progress"] = batch_progress[correlation_id]

        await websocket.send_json(initial_data)

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket, correlation_id, 'batch')
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, correlation_id, 'batch')


@app.get("/api/batch/{correlation_id}/progress")
async def get_batch_progress(correlation_id: str):
    """HTTP endpoint to get current batch progress."""
    if correlation_id in batch_progress:
        return batch_progress[correlation_id]
    else:
        return {
            "correlation_id": correlation_id,
            "status": "not_found"
        }


async def event_listener():
    """
    Background task that listens to RabbitMQ events and broadcasts via WebSocket.
    """
    from events import EventConsumer

    backend = os.getenv('EVENT_BACKEND', 'rabbitmq')

    # Create consumer that listens to ALL document events
    consumer = EventConsumer(
        queue_name='notification-service',
        event_patterns=[
            'document.uploaded',
            'document.classified',
            'document.extracted',
            'document.indexed',
            'batch.*'  # All batch events
        ],
        backend=backend
    )

    def handle_document_event(payload: dict):
        """Handle any document-related event."""
        event_type = payload.get('event_type', 'unknown')
        document_id = payload.get('document_id')
        correlation_id = payload.get('correlation_id')

        logger.info(f"Received event: {event_type} (doc: {document_id}, corr: {correlation_id})")

        # Prepare notification message
        message = {
            "type": "event",
            "event_type": event_type,
            "data": payload,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Broadcast to document subscribers
        if document_id:
            asyncio.create_task(manager.broadcast_to_document(document_id, message))

        # Broadcast to batch subscribers and update batch progress
        if correlation_id:
            # Update batch progress
            if correlation_id not in batch_progress:
                batch_progress[correlation_id] = {
                    "documents": {},
                    "total": 0,
                    "completed": 0,
                    "failed": 0
                }

            progress = batch_progress[correlation_id]

            if document_id:
                progress["documents"][document_id] = {
                    "status": event_type,
                    "updated_at": datetime.utcnow().isoformat()
                }

            # Count completed/failed
            completed = sum(1 for doc in progress["documents"].values()
                          if doc["status"] == "document.indexed")
            failed = sum(1 for doc in progress["documents"].values()
                       if "error" in doc.get("status", ""))

            progress["completed"] = completed
            progress["failed"] = failed
            progress["total"] = len(progress["documents"])

            # Broadcast
            asyncio.create_task(manager.broadcast_to_batch(correlation_id, {
                "type": "progress",
                "progress": progress,
                "event": message,
                "timestamp": datetime.utcnow().isoformat()
            }))

    # Register handlers for all event patterns
    consumer.register_handler('document.uploaded', handle_document_event)
    consumer.register_handler('document.classified', handle_document_event)
    consumer.register_handler('document.extracted', handle_document_event)
    consumer.register_handler('document.indexed', handle_document_event)

    logger.info("Starting event listener...")
    # This blocks, so run in executor
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, consumer.start)


@app.on_event("startup")
async def startup_event():
    """Start the event listener when app starts."""
    logger.info("Starting notification service...")

    # Start event listener in background
    asyncio.create_task(event_listener())


def main():
    """Main entry point."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=os.getenv('LOG_LEVEL', 'INFO')
    )

    # Run FastAPI server
    port = int(os.getenv('PORT', '8001'))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


if __name__ == '__main__':
    main()
