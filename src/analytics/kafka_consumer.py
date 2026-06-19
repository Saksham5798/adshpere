import logging
import json
import time

logger = logging.getLogger("adsphere.analytics.kafka.consumer")

class MockKafkaConsumer:
    """Mock Kafka Consumer for processing asynchronous RTB analytics events."""
    def __init__(self, topic: str, bootstrap_servers='localhost:9092'):
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        logger.info(f"Mock Kafka Consumer listening on topic '{topic}' at {bootstrap_servers}")

    def poll(self, timeout_ms=1000):
        # Emulate polling from partition
        time.sleep(timeout_ms / 1000.0)
        return []

    def commit(self):
        logger.debug("[Kafka Consumer] Offset committed.")
