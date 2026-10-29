import asyncio
import os
import signal
import re
import shlex
import subprocess
import time
from enum import Enum, auto

from .logs import log
from config import DEFAULT_SERVER_PATH, DEFAULT_START_COMMAND, DEBUG, WARNING
from .rcon import RconClient
from .process_utils import bytes_to_mb, get_pid_usage
from .database import db_set_server_status, db_set_server_players, db_set_server_usage, db_get_server
from .database import Server as ServerType


class LocalServer:
    CACHE_TTL: float = 60

    class Status(Enum):
        STARTING = auto()
        RUNNING = auto()
        CLOSING = auto()
        CLOSED = auto()
        UNKNOWN = auto()

    DB_STATUS_TABLE = {
        "starting": Status.STARTING,
        "running": Status.RUNNING,
        "closing": Status.CLOSING,
        "closed": Status.CLOSED,
        "unknown": Status.UNKNOWN,
    }
    STATUS_DB_TABLE = {status: string for string, status in DB_STATUS_TABLE.items()}


    def __init__(self, name: str, *, data: ServerType | None = None):
        self.rcon_conn: RconClient | None = None
        self.name: str = name
        if data:
            self._data = data
            self._data_updated = time.monotonic()
        else:
            self._data: ServerType = {}
            self._data_updated: float = 0
    
    #async def init(self):
        # limits use, always can set it up by hand
        #if await self.get_property('server-port') != await self.port:
        #    await self.set_property('server-port', await self.port)
        #await self.check_health()


    async def is_server_healthy(self, tries: int = 1):
        if await self.is_server_closed():
            return False
        try:
            await self.command("list")
            return True
        except Exception:
            if tries <= 1:
                return False
            return await self.is_server_healthy(tries-1)

    def is_screen_running(self):
        result = subprocess.run(
            ["screen", "-ls"],
            capture_output=True,
            text=True,
            check=False,
        )
        pattern = rf"\.{re.escape(str(self.name))}\s"
        return re.search(pattern, result.stdout) is not None

    async def is_java_running(self):
        path = os.path.realpath(await self.path)
        for entry in os.scandir("/proc"):
            if not entry.name.isdigit():
                continue
            try:
                pid = entry.name
                if ("java" in os.path.basename(os.readlink(f"/proc/{pid}/exe"))
                     and os.path.realpath(f"/proc/{pid}/cwd") == path):
                    return True
            except (FileNotFoundError, PermissionError):
                pass
        return False

    async def is_server_closed(self):
        return not self.is_screen_running() and not await self.is_java_running()

    async def get_players(self) -> tuple[int, int, list[str]]:
        if await self.is_server_closed(): return 0, 0, []

        try:
            text = await self.command("list")
        except Exception as exc:
            log(WARNING, f"RCON error for {self.name}: {exc}")
            return 0, 0, []

        matches = list(re.finditer(
            r"There are (\d+) of a max of (\d+) players online: ?(.*)",
            text,
        ))

        match = matches[-1] if matches else None
        if not match:
            log(WARNING, f"Could not parse player info for {self.name}: {text}")
            return 0, 0, []

        count = int(match.group(1))
        max_count = int(match.group(2))
        raw_names = match.group(3).strip()
        names = [item.strip() for item in raw_names.split(",")] if raw_names else []

        return count, max_count, names

    async def command(self, command: str):
        return await (await self._get_rcon()).command(command)

    async def get_properties(self) -> dict[str, str]:
        properties_path = os.path.join(await self.path, "server.properties")
        properties = {}

        with open(properties_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                properties[key] = value

        return properties

    async def get_property(self, property: str) -> str | None:
        return (await self.get_properties()).get(property)

    async def set_property(self, property: str, new_value: str):
        properties_path = os.path.join(await self.path, "server.properties")

        with open(properties_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        found = False

        with open(properties_path, "w", encoding="utf-8") as file:
            for line in lines:
                if line.startswith(f"{property}="):
                    file.write(f"{property}={new_value}\n")
                    found = True
                else:
                    file.write(line)

            if not found:
                file.write(f"{property}={new_value}\n")

    def quit_screen(self):
        subprocess.run(["screen", "-S", str(self.name), "-X", "quit"])

    def send_screen_command(self, command: str):
        subprocess.run(["screen", "-S", str(self.name), "-X", "stuff", f"{command}\n"])

    async def kill_java(self):
        # Sometimes on neoforge I found that when the server dies, it leaves the java process outside of the screen.
        # Therefore sometimes the kill screen is not enough, then we should purge the java executable.
        path = os.path.realpath(await self.path)
        for entry in os.scandir("/proc"):
            if not entry.name.isdigit():
                continue
            try:
                pid = int(entry.name)
                if ("java" in os.path.basename(os.readlink(f"/proc/{pid}/exe"))
                     and os.path.realpath(f"/proc/{pid}/cwd") == path):
                    os.kill(pid, signal.SIGKILL)
                    return True
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                pass
        return False

    async def get_server_usage(self):
        result = subprocess.run(["screen", "-ls"], capture_output=True)
        match = re.search(rf"\s*(\d+)\.{re.escape(self.name)}\s", result.stdout.decode())
        if match is None:
            return None, None
        ram, cpu = await get_pid_usage(int(match.group(1)))
        return bytes_to_mb(ram), cpu

    async def start(self):
        if await self.is_server_healthy(): return
        if self.is_screen_running(): self.quit_screen()
        if await self.is_java_running(): await self.kill_java()
        await self.set_status(self.Status.STARTING)

        start = (await self.start_command).format(ram_min_mb=await self.ram_min_mb, ram_max_mb=await self.ram_max_mb)
        command = f"cd {shlex.quote(await self.path)} && {start}"
        run_command = (f"screen -dmS {self.name} bash -c '{command}'")
        subprocess.Popen(run_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        #success = await self.wait_until_joinable(120)
        #if success:
        #    self.last_status = self.Status.RUNNING
        #    return True
        #else:
        #   self.last_status = self.Status.UNKNOWN
        #    return False

    async def stop(self):  # WARNING: stop does not check if server properly closed
        if not await self.is_server_healthy():  # could be buggy
            if self.is_screen_running(): self.quit_screen()
            if await self.is_java_running(): await self.kill_java()
            return
        await self.set_status(self.Status.CLOSING)
        try:
            await self.command("kick @a SERVER CLOSING")
            await asyncio.sleep(1)
            await self.command(await self.stop_command)
        except Exception as exc:
            log(WARNING, f"RCON stop failed for {self.name}: {exc}\nStopping via screen.")
            self.send_screen_command("kick @a SERVER CLOSING")
            await asyncio.sleep(1)
            self.send_screen_command(await self.stop_command)

    async def restart(self):
        await self.stop()
        if not await self.wait_until_stopped():
            log(WARNING, f"Server {self.name} failed to stop before restart")
            return
        await self.start()

    async def wait_until_stopped(self, timeout: float = 180) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if await self.is_server_closed():
                return True
            await asyncio.sleep(1)
        return await self.is_server_closed()

    async def read_logs(self, lines: int):
        log_path = os.path.join(await self.path, "logs", "latest.log")
        if not os.path.isfile(log_path):
            return ""
        with open(log_path, "r", encoding="utf-8", errors="ignore") as file:
            return "".join(file.readlines()[-lines:])


    async def set_status(self, new_status: Status):
        new_db_status = self.STATUS_DB_TABLE[new_status]
        self._data["status"] = new_db_status
        self._data["status_updated_at"] = int(time.time())
        await db_set_server_status(self.name, new_db_status)

    async def update_players(self, player_count: int | None, max_player_count: int | None, players: list[str]):
        self._data["player_count"] = player_count
        self._data["max_player_count"] = max_player_count
        self._data["player_nicknames"] = players
        await db_set_server_players(self.name, player_count, max_player_count, players)

    async def update_usage(self, ram: int | None, cpu: float | None):
        self._data["ram_usage_mb"] = ram
        self._data["cpu_usage_percent"] = cpu
        await db_set_server_usage(self.name, ram, cpu)

    async def _get_rcon(self):
        if not self.rcon_conn:
            log(DEBUG, f"starting RCON client for {self.name}")
            self.rcon_conn = RconClient("127.0.0.1", await self.get_property("rcon.port"), await self.get_property("rcon.password"))
        return self.rcon_conn


    async def _get_data(self, force: bool = False) -> ServerType:
        if not force and time.monotonic() - self._data_updated < self.CACHE_TTL:
            return self._data
        self._data = await db_get_server(server=self.name)
        self._data_updated = time.monotonic()
        return self._data
    @property
    async def display_name(self) -> str:
        return (await self._get_data()).get("display_name", self.name)
    @property
    async def status(self) -> Status:
        return self.DB_STATUS_TABLE[(await self._get_data())["status"]]
    @property
    async def status_updated_at(self) -> int:
        return (await self._get_data())["status_updated_at"]
    @property
    async def player_count(self) -> int | None:
        return (await self._get_data())["player_count"]
    @property
    async def max_player_count(self) -> int | None:
        return (await self._get_data())["max_player_count"]
    @property
    async def players(self) -> list[str]:
        return (await self._get_data())["player_nicknames"]
    @property
    async def ram_usage(self) -> int | None:
        return (await self._get_data())["ram_usage_mb"]
    @property
    async def cpu_usage(self) -> float | None:
        return (await self._get_data())["cpu_usage_percent"]
    @property
    async def close_time(self) -> int:
        return (await self._get_data())["close_time"]
    @property
    async def node_id(self) -> str:
        return (await self._get_data())["node_id"]
    @property
    async def host(self) -> str | None:
        return (await self._get_data())["host"]
    @property
    async def port(self) -> int:
        return (await self._get_data())["port"]
    @property
    async def path(self) -> str:
        return ((await self._get_data())["working_directory"] or
                DEFAULT_SERVER_PATH.format(name=self.name))
    @property
    async def start_command(self) -> str:
        return (await self._get_data())["start_command"] or DEFAULT_START_COMMAND
    @property
    async def stop_command(self) -> str:
        return (await self._get_data())["stop_command"] or "stop"
    @property
    async def ram_min_mb(self) -> int:
        return (await self._get_data())["ram_min_mb"]
    @property
    async def ram_max_mb(self) -> int:
        return (await self._get_data())["ram_max_mb"]
