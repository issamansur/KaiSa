import asyncio

class SongQueue:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._playing = None

    async def put(self, song):
        await self._queue.put(song)

    async def get(self):
        if self._playing is not None:
            return self._playing

        try:
            self._playing = await self._queue.get()
            return self._playing
        except asyncio.QueueEmpty:
            return None

    def task_done(self):
        self._playing = None
        self._queue.task_done()

    def clear(self):
        self._queue = asyncio.Queue()
        self._playing = None

    def is_empty(self):
        return self._queue.empty()