import asyncio


class SyncQueue(asyncio.queues.Queue):
    """
    SyncQueue is a zero-sized queue.

    This queue have no internal buffer. Queued item are acquired immediately.

    Note that cancellation of get() and put(item) may be suppressed.
    If no CancelledError is raised, an item is transferred from put(item) to get().
    """

    def __init__(self):
        super().__init__()

        # The following attributes are set by the parent class
        # self._loop = asyncio.get_running_loop()
        # self._getters = collections.deque()
        # self._putters = collections.deque()
        # self._unfinished_tasks = 0
        # self._finished = asyncio.locks.Event()

        self._putter_items = {}

    def _init(self, maxsize):
        pass

    def _get(self):
        raise NotImplementedError

    def _put(self, item):
        raise NotImplementedError

    def qsize(self):
        # Never have items in queue
        return 0

    @property
    def maxsize(self):
        # zero indeed
        return 0

    def empty(self):
        # Always empty
        return True

    def full(self):
        # No items => never full
        return False

    async def put(self, item):
        try:
            return self.put_nowait(item)
        except asyncio.QueueFull:
            pass

        putter = self._loop.create_future()
        self._putter_items[putter] = item
        self._putters.append(putter)

        try:
            await putter
        except asyncio.CancelledError:
            putter.cancel()

            if putter.cancelled():
                self._putters.remove(putter)
                del self._putter_items[putter]
                raise
            # Otherwise, the item have been removed in get_nowait()

    def put_nowait(self, item):
        while self._getters:
            getter = self._getters.popleft()

            if getter.done():
                continue

            getter.set_result(item)
            self._unfinished_tasks += 1
            self._finished.clear()
            return

        raise asyncio.queues.QueueFull

    async def get(self):
        try:
            return self.get_nowait()
        except asyncio.queues.QueueEmpty:
            pass

        getter = self._loop.create_future()
        self._getters.append(getter)

        try:
            await getter
        except asyncio.CancelledError:
            getter.cancel()

            if getter.cancelled():
                self._getters.remove(getter)
                raise
            # Otherwise, an item has been taken and the cancellation is suppressed.

        assert getter.done() and not getter.cancelled()
        return getter.result()

    def get_nowait(self):
        while self._putters:
            putter = self._putters.popleft()
            item = self._putter_items.pop(putter)

            if putter.done():
                continue

            putter.set_result(None)
            return item

        raise asyncio.queues.QueueEmpty
