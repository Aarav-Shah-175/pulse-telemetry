import asyncio
import json
import logging
from collections import defaultdict
from typing import AsyncGenerator, Dict, Optional, Set
import redis.asyncio as aioredis

logger = logging.getLogger("pulse.broker")

class RedisPubSubManager:
    """Async Redis Pub/Sub manager with automatic in-memory fallback for local dev."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self._is_fallback: bool = False
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)

    async def connect(self) -> None:
        """Connects to Redis or enables in-memory fallback if Redis is unavailable."""
        try:
            client = aioredis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=2.0)
            await client.ping()
            self._redis, self._is_fallback = client, False
            logger.info("Connected to Redis broker.")
        except Exception as e:
            self._redis, self._is_fallback = None, True
            logger.warning(f"Redis unavailable ({e}). Using In-Memory Pub/Sub fallback.")

    async def disconnect(self) -> None:
        """Closes Redis connection and cleans up local queues."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
        self._subscribers.clear()

    async def publish(self, tenant_id: str, message: dict) -> int:
        """Publishes metric payload to 'metrics:<tenant_id>'."""
        if self._is_fallback or not self._redis:
            for q in list(self._subscribers[tenant_id]):
                await q.put(message)
            return len(self._subscribers[tenant_id])

        return await self._redis.publish(f"metrics:{tenant_id}", json.dumps(message))

    async def subscribe(self, tenant_id: str) -> AsyncGenerator[dict, None]:
        """Yields deserialized JSON metrics for the given tenant."""
        if self._is_fallback or not self._redis:
            queue: asyncio.Queue = asyncio.Queue(maxsize=100)
            self._subscribers[tenant_id].add(queue)
            try:
                while True:
                    yield await queue.get()
            finally:
                self._subscribers[tenant_id].discard(queue)
            return

        channel = f"metrics:{tenant_id}"
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for item in pubsub.listen():
                if item and item.get("type") == "message" and item.get("data"):
                    try:
                        yield json.loads(item["data"])
                    except json.JSONDecodeError:
                        continue
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
