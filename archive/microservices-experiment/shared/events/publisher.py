"""Event publisher for sending events to the message bus."""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger


class EventPublisher:
    """Publish events to RabbitMQ or Redis Streams."""

    def __init__(self, backend: str = 'rabbitmq'):
        """
        Initialize event publisher.

        Args:
            backend: 'rabbitmq' or 'redis'
        """
        self.backend = backend

        if backend == 'rabbitmq':
            self._init_rabbitmq()
        elif backend == 'redis':
            self._init_redis()
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def _init_rabbitmq(self):
        """Initialize RabbitMQ connection."""
        try:
            import pika

            rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://admin:password@localhost:5672/')
            self.connection = pika.BlockingConnection(
                pika.URLParameters(rabbitmq_url)
            )
            self.channel = self.connection.channel()

            # Declare topic exchange for routing
            self.channel.exchange_declare(
                exchange='documents',
                exchange_type='topic',
                durable=True
            )

            logger.info("RabbitMQ publisher initialized")

        except ImportError:
            logger.error("pika not installed. Install with: pip install pika")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def _init_redis(self):
        """Initialize Redis Streams connection."""
        try:
            import redis

            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()

            logger.info("Redis Streams publisher initialized")

        except ImportError:
            logger.error("redis not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """
        Publish an event to the message bus.

        Args:
            event_type: Event type (e.g., 'document.uploaded', 'document.classified')
            payload: Event data
            correlation_id: Optional correlation ID for tracking related events
        """
        event = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'correlation_id': correlation_id,
            'payload': payload
        }

        try:
            if self.backend == 'rabbitmq':
                self._publish_rabbitmq(event_type, event)
            elif self.backend == 'redis':
                self._publish_redis(event_type, event)

            logger.info(f"Published event: {event_type} (correlation_id: {correlation_id})")

        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            raise

    def _publish_rabbitmq(self, event_type: str, event: Dict[str, Any]):
        """Publish to RabbitMQ."""
        import pika

        self.channel.basic_publish(
            exchange='documents',
            routing_key=event_type,
            body=json.dumps(event),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent message
                content_type='application/json',
                correlation_id=event.get('correlation_id')
            )
        )

    def _publish_redis(self, event_type: str, event: Dict[str, Any]):
        """Publish to Redis Streams."""
        stream_name = f"events:{event_type}"
        self.redis_client.xadd(
            stream_name,
            {'data': json.dumps(event)},
            maxlen=10000  # Keep last 10k events
        )

    def close(self):
        """Close connection to message bus."""
        try:
            if self.backend == 'rabbitmq' and hasattr(self, 'connection'):
                self.connection.close()
            elif self.backend == 'redis' and hasattr(self, 'redis_client'):
                self.redis_client.close()

            logger.info("Event publisher closed")

        except Exception as e:
            logger.error(f"Error closing publisher: {e}")
