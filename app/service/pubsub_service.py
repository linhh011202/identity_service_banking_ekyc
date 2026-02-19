import json
import logging
from datetime import datetime, timezone

from google.cloud import pubsub_v1

from app.core.config import configs

logger = logging.getLogger(__name__)


class PubsubService:
    """Publishes messages to Google Cloud Pub/Sub."""

    def __init__(self) -> None:
        self._project_id = configs.GCP_PROJECT_ID
        self._signup_topic = configs.PUBSUB_SIGNUP_TOPIC
        self._publisher = pubsub_v1.PublisherClient()
        self._topic_path = self._publisher.topic_path(
            self._project_id, self._signup_topic
        )
        logger.info(f"PubsubService initialized — topic: {self._topic_path}")

    def publish_signup_event(self, email: str) -> None:
        """Fire-and-forget publish of a sign-up event."""
        message = {
            "event": "user_ekyc_completed",
            "email": email,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data = json.dumps(message).encode("utf-8")
        future = self._publisher.publish(self._topic_path, data=data)
        future.add_done_callback(lambda f: self._on_publish_done(f, email))

    @staticmethod
    def _on_publish_done(future, email: str) -> None:
        try:
            message_id = future.result()
            logger.info(f"Published sign-up event for {email}, message_id={message_id}")
        except Exception as exc:
            logger.error(f"Failed to publish sign-up event for {email}: {exc}")
