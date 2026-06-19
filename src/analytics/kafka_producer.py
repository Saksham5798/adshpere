import json
import logging

logger = logging.getLogger("adsphere.analytics.kafka.producer")

class MockKafkaProducer:
    """Mock Kafka Producer for streaming RTB analytics events."""
    def __init__(self, bootstrap_servers='localhost:9092'):
        self.bootstrap_servers = bootstrap_servers
        logger.info(f"Initialized Mock Kafka Producer on {bootstrap_servers}")

    def send(self, topic: str, value: dict):
        logger.info(f"[Kafka Producer] Sent event to topic '{topic}': {json.dumps(value)}")
        return True

producer = MockKafkaProducer()
