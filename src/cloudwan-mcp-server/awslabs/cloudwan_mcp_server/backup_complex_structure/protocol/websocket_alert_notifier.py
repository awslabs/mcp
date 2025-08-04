"""
WebSocket Alert Notifier for CloudWAN MCP Real-time Alerting.

This module provides a bridge between the RealtimeAlertingEngine and the 
WebSocketServer, enabling real-time alert notifications to subscribed clients.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

# Import with fallback for different import contexts
try:
    from websocket_server import WebSocketServer, AlertMessage
except ImportError:
    try:
        from .websocket_server import WebSocketServer, AlertMessage
    except ImportError:
        # Fallback when websocket server not available
        WebSocketServer = None
        AlertMessage = None

logger = logging.getLogger(__name__)


class WebSocketAlertNotifier:
    """
    WebSocket Alert Notifier for real-time alert broadcasting.

    Acts as a bridge between the RealtimeAlertingEngine and WebSocketServer,
    converting alert events to WebSocket messages and handling delivery to
    subscribed clients.
    """

    def __init__(self, websocket_server: WebSocketServer):
        """Initialize WebSocket alert notifier"""
        self.websocket_server = websocket_server
        self.notification_queue = asyncio.Queue()
        self.processing_task = None
        self.running = False

        logger.info("WebSocket Alert Notifier initialized")

    async def start(self):
        """Start alert notification processing"""
        if self.running:
            logger.warning("WebSocket Alert Notifier already running")
            return

        self.running = True
        self.processing_task = asyncio.create_task(self._process_notification_queue())

        logger.info("WebSocket Alert Notifier started")

    async def stop(self):
        """Stop alert notification processing"""
        if not self.running:
            return

        self.running = False

        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

        logger.info("WebSocket Alert Notifier stopped")

    async def notify_alert(self, alert_data: Dict[str, Any]):
        """
        Notify alert to WebSocket clients.

        Args:
            alert_data: Alert event data
        """
        try:
            # Queue alert for processing
            await self.notification_queue.put(alert_data)

        except Exception as e:
            logger.error(f"Error queueing alert notification: {str(e)}")

    async def broadcast_system_notification(self, notification_type: str, data: Dict[str, Any]):
        """
        Broadcast system notification to WebSocket clients.

        Args:
            notification_type: Type of notification
            data: Notification data
        """
        try:
            if not self.websocket_server:
                logger.warning("WebSocket server not available for system notification")
                return

            await self.websocket_server.broadcast_message(
                message_type="system_notification",
                data={
                    "notification_type": notification_type,
                    "notification_data": data,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            logger.debug(f"System notification broadcasted: {notification_type}")

        except Exception as e:
            logger.error(f"Error broadcasting system notification: {str(e)}")

    async def _process_notification_queue(self):
        """Process queued alert notifications"""
        while self.running:
            try:
                # Get next alert from queue
                alert_data = await self.notification_queue.get()

                # Process the alert
                await self._process_alert(alert_data)

                # Mark task as done
                self.notification_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing alert notification: {str(e)}")

    async def _process_alert(self, alert_data: Dict[str, Any]):
        """Process single alert notification"""
        try:
            # Check if WebSocket server is available
            if not self.websocket_server:
                logger.warning("WebSocket server not available for alert notification")
                return

            # Create alert message
            alert_message = AlertMessage(
                message_type="alert",
                timestamp=datetime.utcnow().isoformat(),
                data=alert_data,
                message_id=str(uuid.uuid4()),
                severity=alert_data.get("severity", "unknown"),
                resource_id=alert_data.get("resource_id", "unknown"),
                event_id=alert_data.get("event_id", str(uuid.uuid4())),
            )

            # Broadcast via WebSocket server
            await self.websocket_server.broadcast_alert(alert_message)

            logger.debug(f"Alert notification processed: {alert_message.event_id}")

        except Exception as e:
            logger.error(f"Error processing alert: {str(e)}")

    def get_queue_size(self) -> int:
        """Get current notification queue size"""
        return self.notification_queue.qsize() if self.notification_queue else 0
