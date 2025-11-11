import os
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests

# Configure logging
logger = logging.getLogger(__name__)


class WebhookValidator:
    """Handles webhook signature validation and security."""

    def __init__(self, secret_key: Optional[str] = None):
        """Initialize webhook validator with optional secret key."""
        self.secret_key = secret_key or os.getenv("WEBHOOK_SECRET_KEY")

    def validate_google_webhook(self, headers: Dict[str, str], body: str) -> bool:
        """
        Validates Google Calendar webhook signatures.
        Google doesn't use HMAC but we can validate channel tokens.
        """
        try:
            channel_token = headers.get("X-Goog-Channel-Token")
            channel_id = headers.get("X-Goog-Channel-ID")

            # Basic validation - ensure required headers are present
            if not channel_id:
                logger.warning("Missing X-Goog-Channel-ID header in webhook")
                return False

            # You can add custom token validation here if you set tokens during setup
            if channel_token and self.secret_key:
                # Custom validation logic
                expected_token = self._generate_channel_token(channel_id)
                if channel_token != expected_token:
                    logger.warning(f"Invalid channel token for channel {channel_id}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating Google webhook: {e}")
            return False

    def _generate_channel_token(self, channel_id: str) -> str:
        """Generate a secure channel token for validation."""
        if not self.secret_key:
            return ""
        return hmac.new(
            self.secret_key.encode(), channel_id.encode(), hashlib.sha256
        ).hexdigest()


class WebhookProcessor:
    """Processes webhook notifications and handles business logic."""

    def __init__(self):
        """Initialize webhook processor."""
        self.registered_handlers = {}

    def register_handler(self, event_type: str, handler_func):
        """Register a handler function for a specific webhook event type."""
        self.registered_handlers[event_type] = handler_func
        logger.info(f"Registered handler for event type: {event_type}")

    def process_google_calendar_webhook(
        self, webhook_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Google Calendar webhook notifications.

        Args:
            webhook_data: The webhook payload data

        Returns:
            Processing result dictionary
        """
        try:
            resource_state = webhook_data.get("resource_state", "").lower()
            channel_id = webhook_data.get("channel_id")
            resource_uri = webhook_data.get("resource_uri")

            logger.info(
                f"Processing webhook: state={resource_state}, channel={channel_id}"
            )

            # Determine event type based on resource state
            if resource_state == "sync":
                return self._handle_sync_event(webhook_data)
            elif resource_state == "exists":
                return self._handle_event_change(webhook_data)
            elif resource_state == "not_exists":
                return self._handle_event_deletion(webhook_data)
            else:
                logger.warning(f"Unknown resource state: {resource_state}")
                return {"status": "unknown_state", "resource_state": resource_state}

        except Exception as e:
            logger.error(f"Error processing Google Calendar webhook: {e}")
            return {"status": "error", "error": str(e)}

    def _handle_sync_event(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sync webhook events (initial sync)."""
        logger.info("Handling sync event - initial webhook setup")

        # Call registered handler if available
        if "sync" in self.registered_handlers:
            return self.registered_handlers["sync"](webhook_data)

        return {"status": "sync_processed", "message": "Initial sync completed"}

    def _handle_event_change(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle event change notifications."""
        logger.info("Handling event change notification")

        # Extract useful information
        result = {
            "status": "event_changed",
            "channel_id": webhook_data.get("channel_id"),
            "resource_uri": webhook_data.get("resource_uri"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Call registered handler if available
        if "event_change" in self.registered_handlers:
            handler_result = self.registered_handlers["event_change"](webhook_data)
            result.update(handler_result)

        return result

    def _handle_event_deletion(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle event deletion notifications."""
        logger.info("Handling event deletion notification")

        result = {
            "status": "event_deleted",
            "channel_id": webhook_data.get("channel_id"),
            "resource_uri": webhook_data.get("resource_uri"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Call registered handler if available
        if "event_deletion" in self.registered_handlers:
            handler_result = self.registered_handlers["event_deletion"](webhook_data)
            result.update(handler_result)

        return result


class WebhookSubscriptionManager:
    """Manages webhook subscriptions and their lifecycle."""

    def __init__(self):
        """Initialize subscription manager."""
        self.active_subscriptions = {}

    def store_subscription(self, channel_id: str, subscription_data: Dict[str, Any]):
        """Store webhook subscription information."""
        self.active_subscriptions[channel_id] = {
            **subscription_data,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        logger.info(f"Stored subscription for channel: {channel_id}")

    def get_subscription(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve subscription information by channel ID."""
        return self.active_subscriptions.get(channel_id)

    def remove_subscription(self, channel_id: str) -> bool:
        """Remove a webhook subscription."""
        if channel_id in self.active_subscriptions:
            del self.active_subscriptions[channel_id]
            logger.info(f"Removed subscription for channel: {channel_id}")
            return True
        return False

    def list_active_subscriptions(self) -> List[Dict[str, Any]]:
        """List all active webhook subscriptions."""
        return list(self.active_subscriptions.values())

    def cleanup_expired_subscriptions(self):
        """Remove expired webhook subscriptions."""
        # Google Calendar webhooks typically expire after 7 days
        # This would need to check expiration times if stored
        expired_channels = []
        current_time = datetime.utcnow()

        for channel_id, subscription in self.active_subscriptions.items():
            # Check if subscription has expired (implement expiration logic)
            expiration = subscription.get("expiration")
            if expiration:
                # Convert expiration to datetime and compare
                # Implementation depends on expiration format
                pass

        for channel_id in expired_channels:
            self.remove_subscription(channel_id)

        logger.info(f"Cleaned up {len(expired_channels)} expired subscriptions")


class OpenAIWebhookForwarder:
    """Forwards webhook notifications to OpenAI Platform."""

    def __init__(self, openai_endpoint: str, api_key: Optional[str] = None):
        """Initialize OpenAI webhook forwarder."""
        self.openai_endpoint = openai_endpoint
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
            )

    def forward_webhook(
        self, webhook_data: Dict[str, Any], retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Forward webhook data to OpenAI Platform with retry logic.

        Args:
            webhook_data: The webhook payload to forward
            retry_count: Number of retry attempts

        Returns:
            Forwarding result dictionary
        """
        for attempt in range(retry_count):
            try:
                # Prepare payload for OpenAI
                openai_payload = self._prepare_openai_payload(webhook_data)

                response = self.session.post(
                    self.openai_endpoint, json=openai_payload, timeout=30
                )

                response.raise_for_status()

                logger.info(
                    f"Successfully forwarded webhook to OpenAI (attempt {attempt + 1})"
                )

                return {
                    "status": "success",
                    "openai_response_status": response.status_code,
                    "attempt": attempt + 1,
                }

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed to forward webhook to OpenAI: {e}"
                )

                if attempt == retry_count - 1:
                    logger.error(
                        f"Failed to forward webhook to OpenAI after {retry_count} attempts"
                    )
                    return {
                        "status": "failed",
                        "error": str(e),
                        "attempts": retry_count,
                    }

        return {"status": "failed", "error": "Maximum retry attempts exceeded"}

    def _prepare_openai_payload(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare webhook data for OpenAI Platform format."""
        return {
            "type": "calendar_webhook",
            "timestamp": datetime.utcnow().isoformat(),
            "data": webhook_data,
            "source": "google_calendar_mcp",
        }


# Global instances for use in FastAPI endpoints
webhook_validator = WebhookValidator()
webhook_processor = WebhookProcessor()
subscription_manager = WebhookSubscriptionManager()


def setup_default_handlers():
    """Setup default webhook event handlers."""

    def default_event_change_handler(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Default handler for event changes."""
        logger.info("Default event change handler triggered")
        # Add custom processing logic here
        return {"processed": True, "handler": "default_event_change"}

    def default_event_deletion_handler(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Default handler for event deletions."""
        logger.info("Default event deletion handler triggered")
        # Add custom processing logic here
        return {"processed": True, "handler": "default_event_deletion"}

    webhook_processor.register_handler("event_change", default_event_change_handler)
    webhook_processor.register_handler("event_deletion", default_event_deletion_handler)


# Setup default handlers on module import
setup_default_handlers()
