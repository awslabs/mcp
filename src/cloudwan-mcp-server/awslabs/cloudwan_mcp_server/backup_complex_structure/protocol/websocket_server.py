"""
WebSocket Server for CloudWAN MCP Real-time Alerting.

This module provides WebSocket server functionality for real-time alert notifications
with support for client authentication, message broadcasting, and subscription management.
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Set, Any, Callable

import websockets
from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state for WebSocket clients"""

    CONNECTING = "connecting"
    AUTHENTICATED = "authenticated"
    SUBSCRIBED = "subscribed"
    DISCONNECTED = "disconnected"


@dataclass
class WebSocketConnection:
    """Represents a WebSocket client connection"""

    client_id: str
    connection: WebSocketServerProtocol
    state: ConnectionState = ConnectionState.CONNECTING
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    subscriptions: Set[str] = field(default_factory=set)
    user_id: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class WebSocketMessage:
    """Base message format for WebSocket communication"""

    message_type: str
    timestamp: str
    data: Dict[str, Any]
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class AlertMessage(WebSocketMessage):
    """Alert notification message sent over WebSocket"""

    severity: str = "unknown"
    resource_id: str = "unknown"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class WebSocketServer:
    """
    WebSocket server for real-time alerting notifications.

    Provides functionality for:
    - Client connection management
    - Authentication and authorization
    - Message broadcasting
    - Client subscription management
    - Connection health monitoring
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        auth_handler: Optional[Callable] = None,
    ):
        """Initialize WebSocket server"""
        self.host = host
        self.port = port
        self.auth_handler = auth_handler
        self.server = None
        self.connections: Dict[str, WebSocketConnection] = {}
        self.topic_subscriptions = defaultdict(set)  # topic -> client_ids
        self.running = False
        self.heartbeat_task = None

        logger.info(f"WebSocket server initialized on {host}:{port}")

    async def start(self):
        """Start WebSocket server"""
        try:
            if self.running:
                logger.warning("WebSocket server already running")
                return

            self.running = True
            self.server = await websockets.serve(self._handle_connection, self.host, self.port)

            # Start heartbeat monitoring
            self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

            logger.info(f"WebSocket server started on {self.host}:{self.port}")
        except Exception as e:
            self.running = False
            logger.error(f"Failed to start WebSocket server: {str(e)}")
            raise

    async def stop(self):
        """Stop WebSocket server"""
        try:
            if not self.running:
                return

            # Stop heartbeat task
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

            # Close all connections
            close_tasks = []
            for conn in self.connections.values():
                if conn.state != ConnectionState.DISCONNECTED:
                    close_tasks.append(self._close_connection(conn.client_id))

            if close_tasks:
                await asyncio.gather(*close_tasks)

            # Close server
            if self.server:
                self.server.close()
                await self.server.wait_closed()

            self.running = False
            logger.info("WebSocket server stopped")
        except Exception as e:
            logger.error(f"Error stopping WebSocket server: {str(e)}")

    async def broadcast_alert(self, alert_message: AlertMessage):
        """
        Broadcast alert message to subscribed clients.

        Args:
            alert_message: Alert message to broadcast
        """
        try:
            # Convert dataclass to dictionary
            message_dict = asdict(alert_message)
            message_json = json.dumps(message_dict)

            # Get all clients subscribed to this resource and severity
            resource_subscribers = self.topic_subscriptions.get(
                f"resource:{alert_message.resource_id}", set()
            )
            severity_subscribers = self.topic_subscriptions.get(
                f"severity:{alert_message.severity}", set()
            )
            all_subscribers = self.topic_subscriptions.get("all", set())

            # Combine subscribers
            subscribers = resource_subscribers | severity_subscribers | all_subscribers

            # Broadcast to all subscribers
            send_tasks = []
            for client_id in subscribers:
                if (
                    client_id in self.connections
                    and self.connections[client_id].state == ConnectionState.SUBSCRIBED
                ):
                    send_tasks.append(self._send_message(client_id, message_json))

            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)

            logger.debug(
                f"Alert broadcasted to {len(send_tasks)} clients",
                severity=alert_message.severity,
                event_id=alert_message.event_id,
            )

        except Exception as e:
            logger.error(f"Error broadcasting alert: {str(e)}")

    async def broadcast_message(
        self, message_type: str, data: Dict[str, Any], topic: Optional[str] = None
    ):
        """
        Broadcast a generic message to clients.

        Args:
            message_type: Type of message
            data: Message data
            topic: Optional topic filter for subscribers
        """
        try:
            message = WebSocketMessage(
                message_type=message_type,
                timestamp=datetime.utcnow().isoformat(),
                data=data,
            )
            message_json = json.dumps(asdict(message))

            # Determine recipients
            recipients = set()
            if topic:
                recipients = self.topic_subscriptions.get(topic, set())
            else:
                # Send to all connected clients
                recipients = {
                    client_id
                    for client_id, conn in self.connections.items()
                    if conn.state in [ConnectionState.AUTHENTICATED, ConnectionState.SUBSCRIBED]
                }

            # Send to all recipients
            send_tasks = []
            for client_id in recipients:
                send_tasks.append(self._send_message(client_id, message_json))

            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)

            logger.debug(f"Message broadcasted to {len(send_tasks)} clients", type=message_type)
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")

    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        client_id = str(uuid.uuid4())

        try:
            # Register new connection
            self.connections[client_id] = WebSocketConnection(
                client_id=client_id,
                connection=websocket,
                user_agent=websocket.request_headers.get("User-Agent"),
            )

            logger.info(f"New WebSocket connection: {client_id}")

            # Send welcome message
            await websocket.send(
                json.dumps(
                    {
                        "message_type": "welcome",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "client_id": client_id,
                            "message": "Welcome to CloudWAN MCP Real-time Alerting WebSocket Server",
                            "auth_required": self.auth_handler is not None,
                        },
                    }
                )
            )

            # Process messages
            async for message in websocket:
                await self._process_message(client_id, message)

                # Update activity timestamp
                if client_id in self.connections:
                    self.connections[client_id].last_activity = time.time()

        except ConnectionClosed:
            logger.info(f"WebSocket connection closed: {client_id}")
        except Exception as e:
            logger.error(f"Error handling WebSocket connection: {str(e)}")
        finally:
            await self._close_connection(client_id)

    async def _process_message(self, client_id: str, message: str):
        """Process incoming WebSocket message"""
        try:
            if client_id not in self.connections:
                return

            data = json.loads(message)
            message_type = data.get("message_type", "")

            if message_type == "authenticate":
                await self._handle_authentication(client_id, data)
            elif message_type == "subscribe":
                await self._handle_subscription(client_id, data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscription(client_id, data)
            elif message_type == "ping":
                await self._handle_ping(client_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self._send_message(
                    client_id,
                    json.dumps(
                        {
                            "message_type": "error",
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": {
                                "error": "Unknown message type",
                                "code": "UNKNOWN_MESSAGE_TYPE",
                            },
                        }
                    ),
                )

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message from client: {client_id}")
            await self._send_message(
                client_id,
                json.dumps(
                    {
                        "message_type": "error",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "error": "Invalid JSON message",
                            "code": "INVALID_JSON",
                        },
                    }
                ),
            )
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    async def _handle_authentication(self, client_id: str, data: Dict[str, Any]):
        """Handle authentication message"""
        if client_id not in self.connections:
            return

        conn = self.connections[client_id]

        # Skip authentication if no auth handler configured
        if not self.auth_handler:
            conn.state = ConnectionState.AUTHENTICATED
            await self._send_message(
                client_id,
                json.dumps(
                    {
                        "message_type": "authenticated",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {"status": "success", "client_id": client_id},
                    }
                ),
            )
            return

        # Extract auth token
        auth_token = data.get("data", {}).get("token")
        if not auth_token:
            await self._send_message(
                client_id,
                json.dumps(
                    {
                        "message_type": "error",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "error": "Authentication token required",
                            "code": "AUTH_TOKEN_REQUIRED",
                        },
                    }
                ),
            )
            return

        # Authenticate with provided handler
        try:
            auth_result = await self.auth_handler(auth_token)
            if auth_result.get("success"):
                # Update connection with authenticated user
                conn.state = ConnectionState.AUTHENTICATED
                conn.user_id = auth_result.get("user_id")

                await self._send_message(
                    client_id,
                    json.dumps(
                        {
                            "message_type": "authenticated",
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": {
                                "status": "success",
                                "client_id": client_id,
                                "user_id": conn.user_id,
                            },
                        }
                    ),
                )

                logger.info(f"Client authenticated: {client_id}, user_id: {conn.user_id}")
            else:
                await self._send_message(
                    client_id,
                    json.dumps(
                        {
                            "message_type": "error",
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": {
                                "error": "Authentication failed",
                                "code": "AUTH_FAILED",
                                "details": auth_result.get("message", "Invalid credentials"),
                            },
                        }
                    ),
                )

                # Close connection after authentication failure
                await self._close_connection(client_id)

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            await self._send_message(
                client_id,
                json.dumps(
                    {
                        "message_type": "error",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {"error": "Authentication error", "code": "AUTH_ERROR"},
                    }
                ),
            )

    async def _handle_subscription(self, client_id: str, data: Dict[str, Any]):
        """Handle subscription message"""
        if client_id not in self.connections:
            return

        conn = self.connections[client_id]

        # Verify client is authenticated
        if conn.state != ConnectionState.AUTHENTICATED and conn.state != ConnectionState.SUBSCRIBED:
            await self._send_message(
                client_id,
                json.dumps(
                    {
                        "message_type": "error",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "error": "Authentication required before subscribing",
                            "code": "AUTH_REQUIRED",
                        },
                    }
                ),
            )
            return

        # Process subscription
        try:
            subscriptions = data.get("data", {}).get("topics", [])
            if not subscriptions:
                subscriptions = ["all"]  # Default subscription to all alerts

            # Add subscriptions
            for topic in subscriptions:
                self.topic_subscriptions[topic].add(client_id)
                conn.subscriptions.add(topic)

            # Update connection state
            conn.state = ConnectionState.SUBSCRIBED

            # Send confirmation
            await self._send_message(
                client_id,
                json.dumps(
                    {
                        "message_type": "subscribed",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "subscriptions": list(conn.subscriptions),
                            "status": "success",
                        },
                    }
                ),
            )

            logger.info(f"Client subscribed: {client_id}, topics: {list(conn.subscriptions)}")

        except Exception as e:
            logger.error(f"Subscription error: {str(e)}")
            await self._send_message(
                client_id,
                json.dumps(
                    {
                        "message_type": "error",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "error": "Subscription error",
                            "code": "SUBSCRIPTION_ERROR",
                        },
                    }
                ),
            )

    async def _handle_unsubscription(self, client_id: str, data: Dict[str, Any]):
        """Handle unsubscription message"""
        if client_id not in self.connections:
            return

        conn = self.connections[client_id]

        # Process unsubscription
        try:
            topics = data.get("data", {}).get("topics", [])

            if not topics:
                # Unsubscribe from all
                for topic in list(conn.subscriptions):
                    if client_id in self.topic_subscriptions[topic]:
                        self.topic_subscriptions[topic].remove(client_id)
                conn.subscriptions.clear()
            else:
                # Unsubscribe from specified topics
                for topic in topics:
                    if topic in conn.subscriptions:
                        conn.subscriptions.remove(topic)

                    if (
                        topic in self.topic_subscriptions
                        and client_id in self.topic_subscriptions[topic]
                    ):
                        self.topic_subscriptions[topic].remove(client_id)

            # Send confirmation
            await self._send_message(
                client_id,
                json.dumps(
                    {
                        "message_type": "unsubscribed",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "remaining_subscriptions": list(conn.subscriptions),
                            "status": "success",
                        },
                    }
                ),
            )

        except Exception as e:
            logger.error(f"Unsubscription error: {str(e)}")
            await self._send_message(
                client_id,
                json.dumps(
                    {
                        "message_type": "error",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "error": "Unsubscription error",
                            "code": "UNSUBSCRIPTION_ERROR",
                        },
                    }
                ),
            )

    async def _handle_ping(self, client_id: str):
        """Handle ping message"""
        if client_id not in self.connections:
            return

        # Send pong response
        await self._send_message(
            client_id,
            json.dumps(
                {
                    "message_type": "pong",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"server_time": time.time()},
                }
            ),
        )

    async def _send_message(self, client_id: str, message: str):
        """Send message to specific client"""
        if client_id not in self.connections:
            return

        conn = self.connections[client_id]

        try:
            await conn.connection.send(message)
        except ConnectionClosed:
            await self._close_connection(client_id)
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {str(e)}")

    async def _close_connection(self, client_id: str):
        """Close and cleanup client connection"""
        if client_id not in self.connections:
            return

        conn = self.connections[client_id]

        try:
            # Remove from topic subscriptions
            for topic in conn.subscriptions:
                if (
                    topic in self.topic_subscriptions
                    and client_id in self.topic_subscriptions[topic]
                ):
                    self.topic_subscriptions[topic].remove(client_id)

            # Close connection
            if conn.state != ConnectionState.DISCONNECTED:
                await conn.connection.close()

            # Update state
            conn.state = ConnectionState.DISCONNECTED

            # Clean up connections (after a delay to handle reconnects)
            asyncio.create_task(self._delayed_connection_cleanup(client_id))

            logger.info(f"Connection closed: {client_id}")

        except Exception as e:
            logger.error(f"Error closing connection {client_id}: {str(e)}")

    async def _delayed_connection_cleanup(self, client_id: str):
        """Clean up connection after delay (allows for reconnection handling)"""
        await asyncio.sleep(60)  # Wait 60s before removing

        if (
            client_id in self.connections
            and self.connections[client_id].state == ConnectionState.DISCONNECTED
        ):
            del self.connections[client_id]

    async def _heartbeat_monitor(self):
        """Monitor connections for heartbeats and timeouts"""
        while self.running:
            try:
                current_time = time.time()
                stale_connections = []

                # Check all connections for timeouts
                for client_id, conn in self.connections.items():
                    if conn.state == ConnectionState.DISCONNECTED:
                        continue

                    # Check if connection is stale (no activity for 60 seconds)
                    if current_time - conn.last_activity > 60:
                        stale_connections.append(client_id)

                # Close stale connections
                for client_id in stale_connections:
                    logger.warning(f"Closing stale connection: {client_id}")
                    await self._close_connection(client_id)

                # Send periodic heartbeat to active clients
                stats = self.get_connection_stats()
                heartbeat_message = {
                    "message_type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "server_time": current_time,
                        "active_connections": stats["active_connections"],
                        "server_uptime": time.time() - stats["server_start_time"],
                    },
                }

                send_tasks = []
                for client_id, conn in self.connections.items():
                    if conn.state in [
                        ConnectionState.AUTHENTICATED,
                        ConnectionState.SUBSCRIBED,
                    ]:
                        send_tasks.append(
                            self._send_message(client_id, json.dumps(heartbeat_message))
                        )

                if send_tasks:
                    await asyncio.gather(*send_tasks, return_exceptions=True)

                await asyncio.sleep(15)  # Check every 15 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {str(e)}")
                await asyncio.sleep(30)  # Longer wait on error

    def get_connection_stats(self):
        """Get WebSocket connection statistics"""
        active_connections = 0
        subscribed_connections = 0
        authenticated_connections = 0

        for conn in self.connections.values():
            if conn.state != ConnectionState.DISCONNECTED:
                active_connections += 1

            if conn.state == ConnectionState.SUBSCRIBED:
                subscribed_connections += 1
            elif conn.state == ConnectionState.AUTHENTICATED:
                authenticated_connections += 1

        topic_stats = {topic: len(clients) for topic, clients in self.topic_subscriptions.items()}

        return {
            "active_connections": active_connections,
            "subscribed_connections": subscribed_connections,
            "authenticated_connections": authenticated_connections,
            "topics": topic_stats,
            "server_start_time": time.time()
            - (
                self.heartbeat_task.get_coro().cr_frame.f_locals["current_time"]
                if self.heartbeat_task
                else time.time()
            ),
            "running": self.running,
        }
