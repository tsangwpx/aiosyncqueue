import asyncio
import collections
from typing import Dict, Any


class SyncQueue(asyncio.queues.Queue):
    # Some typing hints for internal uses
    _loop: asyncio.events.AbstractEventLoop
    _getters: collections.deque
    _putters: collections.deque
    _unfinished_tasks: int
    _finished: asyncio.locks.Event
    _putter_items: Dict[asyncio.Future, Any]
