class forasync():
    def __init__(self, obj: list):
        """Creates an asynchronous iterator from a non-asynchronous 1-dimensional obj.

        Args:
            obj: the object to asynchronously iterate over.
        """
        self.obj = obj

        self.i = -1
        self.end = len(obj) - 1

    def __aiter__(self):
        return self

    async def next(self):
        self.i += 1
        return self.obj[self.i]

    async def __anext__(self):
        if self.i >= self.end:
            raise StopAsyncIteration
        else:
            return await self.next()