"""Event consumer for receiving events from the message bus."""

import json
import os
from typing import Callable, Dict, List
from loguru import logger


class EventConsumer:
    """Consume events from RabbitMQ or Redis Streams."""

    def __init__(
        self,
        queue_name: str,
        event_patterns: List[str],
        backend: str = 'rabbitmq'
    ):
        """
        Initialize event consumer.

        Args:
            queue_name: Unique queue name for this consumer
            event_patterns: List of event patterns to subscribe to (e.g., ['document.uploaded'])
            backend: 'rabbitmq' or 'redis'
        """
        self.queue_name = queue_name
        self.event_patterns = event_patterns
        self.backend = backend
        self.handlers: Dict[str, Callable] = {}

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

            # Declare exchange
            self.channel.exchange_declare(
                exchange='documents',
                exchange_type='topic',
                durable=True
            )

            # Declare queue with dead-letter exchange
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': 'documents-dlx',
                    'x-dead-letter-routing-key': 'dead-letter'
                }
            )

            # Declare dead-letter exchange and queue
            self.channel.exchange_declare(
                exchange='documents-dlx',
                exchange_type='direct',
                durable=True
            )
            self.channel.queue_declare(queue='dead-letter-queue', durable=True)
            self.channel.queue_bind(
                exchange='documents-dlx',
                queue='dead-letter-queue',
                routing_key='dead-letter'
            )

            # Bind queue to event patterns
            for pattern in self.event_patterns:
                self.channel.queue_bind(
                    exchange='documents',
                    queue=self.queue_name,
                    routing_key=pattern
                )

            # Set QoS to process one message at a time
            self.channel.basic_qos(prefetch_count=1)

            logger.info(f"RabbitMQ consumer initialized for queue: {self.queue_name}")

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

            # Create consumer group for each event pattern
            for pattern in self.event_patterns:
                stream_name = f"events:{pattern}"
                try:
                    self.redis_client.xgroup_create(
                        stream_name,
                        self.queue_name,
                        id='0',
                        mkstream=True
                    )
                except Exception:
                    # Group already exists
                    pass

            logger.info(f"Redis Streams consumer initialized for queue: {self.queue_name}")

        except ImportError:
            logger.error("redis not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def register_handler(self, event_type: str, handler: Callable):
        """
        Register a handler function for an event type.

        Args:
            event_type: Event type to handle
            handler: Function that takes event payload as argument
        """
        self.handlers[event_type] = handler
        logger.info(f"Registered handler for event: {event_type}")

    def start(self):
        """Start consuming events."""
        logger.info(f"Starting consumer for patterns: {self.event_patterns}")

        if self.backend == 'rabbitmq':
            self._start_rabbitmq()
        elif self.backend == 'redis':
            self._start_redis()

    def _start_rabbitmq(self):
        """Start consuming from RabbitMQ."""
        def callback(ch, method, properties, body):
            try:
                event = json.loads(body)
                event_type = event['event_type']
                correlation_id = event.get('correlation_id')

                logger.info(
                    f"Received event: {event_type} "
                    f"(correlation_id: {correlation_id})"
                )

                if event_type in self.handlers:
                    # Call handler
                    self.handlers[event_type](event['payload'])

                    # Acknowledge message
                    ch.basic_ack(delivery_tag=method.delivery_tag)

                    logger.success(
                        f"Processed event: {event_type} "
                        f"(correlation_id: {correlation_id})"
                    )
                else:
                    logger.warning(f"No handler for event type: {event_type}")
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                logger.error(f"Error processing event: {e}")
                # Reject and don't requeue (goes to DLQ)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=callback
        )

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.channel.stop_consuming()
            self.connection.close()

    def _start_redis(self):
        """Start consuming from Redis Streams."""
        consumer_name = os.getenv('HOSTNAME', 'consumer-1')

        while True:
            try:
                for pattern in self.event_patterns:
                    stream_name = f"events:{pattern}"

                    # Read from stream
                    messages = self.redis_client.xreadgroup(
                        groupname=self.queue_name,
                        consumername=consumer_name,
                        streams={stream_name: '>'},
                        count=10,
                        block=5000
                    )

                    for stream, msg_list in messages:
                        for msg_id, data in msg_list:
                            try:
                                event = json.loads(data[b'data'])
                                event_type = event['event_type']
                                correlation_id = event.get('correlation_id')

                                logger.info(
                                    f"Received event: {event_type} "
                                    f"(correlation_id: {correlation_id})"
                                )

                                if event_type in self.handlers:
                                    # Call handler
                                    self.handlers[event_type](event['payload'])

                                    # Acknowledge message
                                    self.redis_client.xack(
                                        stream_name,
                                        self.queue_name,
                                        msg_id
                                    )

                                    logger.success(
                                        f"Processed event: {event_type} "
                                        f"(correlation_id: {correlation_id})"
                                    )

                            except Exception as e:
                                logger.error(f"Error processing event: {e}")
                                # Don't ack - message will be redelivered

            except KeyboardInterrupt:
                logger.info("Stopping consumer...")
                break
            except Exception as e:
                logger.error(f"Consumer error: {e}")

    def close(self):
        """Close connection to message bus."""
        try:
            if self.backend == 'rabbitmq' and hasattr(self, 'connection'):
                self.connection.close()
            elif self.backend == 'redis' and hasattr(self, 'redis_client'):
                self.redis_client.close()

            logger.info("Event consumer closed")

        except Exception as e:
            logger.error(f"Error closing consumer: {e}")
