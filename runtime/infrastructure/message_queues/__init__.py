"""Message queue implementations and factory."""

from ...core.message_queue import MessageQueueInterface
from .in_memory import InMemoryMessageQueue
from .redis import RedisMessageQueue
from .rabbitmq import RabbitMQMessageQueue

__all__ = [
    "MessageQueueInterface",
    "InMemoryMessageQueue", 
    "RedisMessageQueue",
    "RabbitMQMessageQueue",
    "create_message_queue"
]


def create_message_queue(queue_type: str = "memory", **kwargs) -> MessageQueueInterface:
    """Factory function to create message queue implementations.
    
    Args:
        queue_type: Type of queue to create ("memory", "redis", "rabbitmq")
        **kwargs: Additional configuration parameters for specific queue types
        
    Returns:
        MessageQueueInterface implementation
        
    Raises:
        ValueError: If queue_type is not supported
        
    Examples:
        # Create in-memory queue for development/testing
        queue = create_message_queue("memory")
        
        # Create Redis queue
        queue = create_message_queue("redis", redis_url="redis://localhost:6379")
        
        # Create RabbitMQ queue
        queue = create_message_queue("rabbitmq", amqp_url="amqp://localhost:5672")
    """
    if queue_type == "memory":
        return InMemoryMessageQueue()
    elif queue_type == "redis":
        return RedisMessageQueue(kwargs.get("redis_url", "redis://localhost:6379"))
    elif queue_type == "rabbitmq":
        return RabbitMQMessageQueue(kwargs.get("amqp_url", "amqp://localhost:5672"))
    else:
        raise ValueError(f"Unsupported queue type: {queue_type}")
