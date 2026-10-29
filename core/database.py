import asyncio
import aiohttp
import json
from urllib.parse import quote
from typing import cast, TypedDict

from globals import Globals
from config import ERROR, WARNING, CRITICAL, DATABASE_API, API_SERVICE
from .utils import network_working
from .logs import log
from .verify import make_signature_headers, verify_response_signature


async def _db_send(path: str, method: str, body: bytes = b"", timeout: float = 5, decode_json: bool = True, tries: int = 3, retry_delay: float = 0.5) -> bytes | int | str | dict[str, str|dict[str, str]]:
    url = DATABASE_API + path
    method = method.upper()
    body = body if method not in ("GET", "HEAD") else b""
    aiohttp_timeout = aiohttp.ClientTimeout(total=timeout)
    for attempt in range(tries):
        headers, nonce = make_signature_headers(
            private_key=Globals.priv_key,
            method=method,
            path=path,
            body_bytes=body,
        )
        headers["X-Service"] = API_SERVICE
        if body:
            headers["Content-Type"] = "application/json"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp_timeout) as session:
                async with session.request(
                    method=method,
                    url=url,
                    data=body,
                    headers=headers,
                ) as response:
                    response_body = await response.read()
                    if not verify_response_signature(Globals.auth_map.get("database"), response.status, response_body, response.headers, nonce):
                        log(CRITICAL, "Database COULD NOT VERIFY")
                        raise RuntimeError("Database COULD NOT VERIFY")
                    if response.status >= 400:
                        log(ERROR, f"Database API error {response.status}: {response_body.decode(errors='replace')}")
                        raise RuntimeError(f"Database API error {response.status}: {response_body.decode(errors='replace')}")
                    if decode_json:
                        return json.loads(response_body.decode())
                    else:
                        return response_body
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError) as exc:
            error = "Database API request timed out" if isinstance(exc, asyncio.TimeoutError) else "Could not connect to Database API"
            if attempt + 1 >= tries:
                log(ERROR, f"{error}; {exc} (attempt {attempt + 1}/{tries})")
                raise RuntimeError(error) from exc
            if not network_working():
                log(WARNING(to_discord=True), f"{error}; {exc} (attempt {attempt + 1}/{tries})")
            await asyncio.sleep(retry_delay)
        except aiohttp.ClientError as exc:
            log(ERROR, f"Database API request failed: {exc}")
            raise RuntimeError(f"Database API request failed: {exc}") from exc


class Permissions(TypedDict):
    users: dict[str, dict[str, int]]
    guilds: dict[str, dict[str, int]]
    roles: dict[str, dict[str, int]]
    globals: dict[str, int]
class Server(TypedDict):
    name: str
    display_name: str
    node_id: str
    status: str
    status_updated_at: int
    player_count: int | None
    max_player_count: int | None
    player_nicknames: list[str]
    ram_usage_mb: int | None
    cpu_usage_percent: float | None
    close_time: int
    host: str | None
    port: int
    ram_min_mb: int
    ram_max_mb: int
    start_command: str | None
    stop_command: str | None
    working_directory: str | None
type Servers = dict[str, Server]  # TECHNICALLY Server should not have the name:str thus this is incorrect
type Node = dict[str, str]

async def db_get_permissions() -> Permissions:
    pp = cast(dict, await _db_send("/get_perms", "GET"))
    pp["globals"] = pp.get("global", {})
    return cast(Permissions, pp)

async def db_get_servers() -> Servers:
    return cast(Servers, await _db_send("/servers", "GET"))

async def db_get_server(server: str) -> Server:
    return cast(Server, cast(object, await _db_send(f"/server/{quote(str(server))}", "GET")))

async def db_get_node(node: str) -> Node:
    return cast(Node, await _db_send(f"/node/{quote(str(node))}", "GET"))

async def db_set_server_status(server: str, status: str) -> None:
    await _db_send(f"/server/{quote(str(server))}/status", "POST", json.dumps(status).encode())

async def db_set_server_players(server: str, player_count: int | None, max_player_count: int | None, player_nicknames: list[str] | None) -> None:
    await _db_send(
        f"/server/{quote(str(server))}/players", "POST", json.dumps({
            "player_count": player_count,
            "max_player_count": max_player_count,
            "player_nicknames": player_nicknames
        }).encode()
    )

async def db_set_server_usage(server: str, ram_usage_mb: int | None, cpu_usage_percent: float | None) -> None:
    await _db_send(
        f"/server/{quote(str(server))}/usage", "POST", json.dumps({
            "ram_usage_mb": ram_usage_mb,
            "cpu_usage_percent": cpu_usage_percent
        }).encode()
    )
