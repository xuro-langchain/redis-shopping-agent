from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.redis import RedisStore

from agents.utils import get_redis_client


# Singleton instances
_checkpointer: RedisSaver | None = None
_store: RedisStore | None = None


def get_checkpointer() -> RedisSaver:
    """
    Get a shared RedisSaver checkpointer instance.
    Creates and sets up the checkpointer on first call, then reuses it.
    """
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = RedisSaver(redis_client=get_redis_client())
        _checkpointer.setup()
    return _checkpointer


def get_store(namespace: str) -> RedisStore:
    """
    Get a shared RedisStore instance for long-term memory.
    Creates the store on first call, then reuses it.
    """
    global _store
    if _store is None:
        _store = RedisStore(conn=get_redis_client(), store_prefix=namespace)
        _store.setup()
    return _store

