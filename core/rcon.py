import asyncio

from aiomcrcon import Client


class RconClient:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.client = None
        self.lock = asyncio.Lock()

    async def _connect_sync(self):
        await self.close_sync()
        try:
            self.client = Client(self.host, self.port, self.password)
            await self.client.connect()
        except Exception:
            self.client = None

    async def close_sync(self):
        if self.client is None:
            return
        try:
            await self.client.close()
        except Exception:
            pass
        self.client = None

    async def _command_sync(self, command):
        if self.client is None:
            await self._connect_sync()

        # send_cmd RETURNS ("response", response_id)
        try:
            return (await self.client.send_cmd(command))[0]
        except Exception:
            await self._connect_sync()
            return (await self.client.send_cmd(command))[0]

    async def command(self, command):
        async with self.lock:
            return await self._command_sync(command)

    async def close(self):
        async with self.lock:
            await self.close_sync()