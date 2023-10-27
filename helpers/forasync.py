# Imports
from discord import Guild


class forasync():
    def __init__(self, obj: list[any]):
        """Creates an asynchronous iterator from a non asynchronous 1-dimensional list

        Args:
            iterable (list[any]): the list to asynchronously iterate over
        """
        self.list = obj

        self.i = -1
        self.end = len(obj) - 1

    def __aiter__(self):
        return self

    async def next(self) -> Guild:
        self.i += 1
        return self.list[self.i]

    async def __anext__(self):
        if self.i >= self.end:
            raise StopAsyncIteration
        else:
            print(self.i)
            return await self.next()