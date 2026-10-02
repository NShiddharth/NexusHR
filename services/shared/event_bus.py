import os
import json
import logging
import asyncio
from typing import Callable, Dict, List
import pika

logger = logging.getLogger("event_bus")

class EventBus:
    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.use_mock = os.getenv("EVENT_BUS_MODE", "mock").lower() == "mock"
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        logger.info(f"Subscribed handler to event: {event_type}")

    async def publish(self, event_type: str, payload: dict, source_service: str = "unknown"):
        event = {
            "event_type": event_type,
            "source_service": source_service,
            "payload": payload
        }
        logger.info(f"EventBus Publishing [{event_type}] from {source_service}: {payload}")
        
        # Local in-memory dispatch to registered listeners
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(event))
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in subscriber callback for {event_type}: {e}")

        # Wildcard subscribers (e.g. "*")
        if "*" in self.subscribers:
            for callback in self.subscribers["*"]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(event))
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in wildcard callback for {event_type}: {e}")

        # If connected to rabbitmq in production/docker
        if not self.use_mock:
            try:
                params = pika.URLParameters(self.rabbitmq_url)
                connection = pika.BlockingConnection(params)
                channel = connection.channel()
                channel.exchange_declare(exchange='employee_events', exchange_type='topic', durable=True)
                channel.basic_publish(
                    exchange='employee_events',
                    routing_key=event_type,
                    body=json.dumps(event)
                )
                connection.close()
            except Exception as e:
                logger.debug(f"RabbitMQ dispatch note (using in-memory): {e}")

event_bus = EventBus()
