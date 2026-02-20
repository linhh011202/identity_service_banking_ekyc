import json
import logging
from datetime import datetime, timezone

from app.core.config import configs
from app.core.constants import Event

logger = logging.getLogger(__name__)


class PubsubService:
    """Publishes messages to Google Cloud Pub/Sub.

    Uses lazy initialisation so the app can still start even when
    GCP credentials are not available (e.g. local development).
    """

    def __init__(self) -> None:
        self._project_id = configs.GCP_PROJECT_ID
        self._signup_topic = configs.PUBSUB_SIGNUP_TOPIC
        self._signin_topic = configs.PUBSUB_SIGNIN_TOPIC
        self._publisher = None
        self._signup_topic_path: str | None = None
        self._signin_topic_path: str | None = None
        logger.info("PubsubService created (publisher will be initialised lazily)")

    def _get_publisher(self):
        """Lazy-init the PublisherClient on first use."""
        if self._publisher is None:
            from google.cloud import pubsub_v1

            self._publisher = pubsub_v1.PublisherClient()
            self._signup_topic_path = self._publisher.topic_path(
                self._project_id, self._signup_topic
            )
            self._signin_topic_path = self._publisher.topic_path(
                self._project_id, self._signin_topic
            )
            logger.info(
                f"Pub/Sub publisher initialised — signup: {self._signup_topic_path}, signin: {self._signin_topic_path}"
            )
        return self._publisher

    def publish_signup_event(self, email: str, session_id: str) -> None:
        """Fire-and-forget publish of a sign-up event."""
        try:
            publisher = self._get_publisher()
        except Exception as exc:
            logger.warning(f"Pub/Sub unavailable, skipping publish for {email}: {exc}")
            return

        message = {
            "event": Event.SIGN_UP,
            "email": email,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data = json.dumps(message).encode("utf-8")
        future = publisher.publish(self._signup_topic_path, data=data)
        future.add_done_callback(
            lambda f: self._on_publish_done(f, email, Event.SIGN_UP)
        )

    def publish_signin_event(self, email: str, session_id: str) -> None:
        """Fire-and-forget publish of a sign-in event."""
        try:
            publisher = self._get_publisher()
        except Exception as exc:
            logger.warning(f"Pub/Sub unavailable, skipping publish for {email}: {exc}")
            return

        message = {
            "event": Event.SIGN_IN,
            "email": email,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data = json.dumps(message).encode("utf-8")
        future = publisher.publish(self._signin_topic_path, data=data)
        future.add_done_callback(
            lambda f: self._on_publish_done(f, email, Event.SIGN_IN)
        )

    @staticmethod
    def _on_publish_done(future, email: str, event_type: str) -> None:
        try:
            message_id = future.result()
            logger.info(
                f"Published {event_type} event for {email}, message_id={message_id}"
            )
        except Exception as exc:
            logger.error(f"Failed to publish {event_type} event for {email}: {exc}")
