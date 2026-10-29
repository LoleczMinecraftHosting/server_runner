import asyncio
import time
import threading
from urllib import request
import ssl
import json
from http.server import ThreadingHTTPServer

from core.utils import format_traceback
from core.mc_server import LocalServer
from core.database import db_get_servers
from core.logs import log
from core.verify import load_private_key, load_auth_map
from api.api_core import APIHandler
from globals import Globals
from config import (
    NODE_NAME, PRIVKEY_DIR, AUTH_MAP_LINK, API_PORT,
    SERVER_START_TIMEOUT, SERVER_STOP_TIMEOUT, LOOP_REFRESH,
    INFO, QINFO, WARNING, ERROR, CRITICAL)

Status = LocalServer.Status


stop_tasks = set()


if PRIVKEY_DIR.exists():
    Globals.priv_key = load_private_key(path=PRIVKEY_DIR)
else:
    log(CRITICAL, f"Missing priv key at {PRIVKEY_DIR}")
    exit(-11)
try:
    with request.urlopen(AUTH_MAP_LINK, context=ssl.create_default_context()) as r:
        raw_auth_map = json.loads(r.read().decode())
    Globals.auth_map = load_auth_map(raw_auth_map)
except Exception as e:
    log(CRITICAL, f"error while getting auth_map from {AUTH_MAP_LINK};\n{e}")
    exit(-10)


async def load_servers():
    servers_data = await db_get_servers()
    unused = set(Globals.servers.keys())
    for server_name, s_data in servers_data.items():
        s_data["name"] = server_name  # Not given via db_get_servers
        if s_data["node_id"] == NODE_NAME:
            if s_data["name"] in Globals.servers:
                unused.remove(s_data["name"])
                if isinstance(Globals.servers[s_data["name"]], LocalServer):
                    continue  # Already loaded
                #  del self.servers[s_data["name"]]
            log(INFO, f"SM; Loading Local server {s_data["name"]}")
            new_serv = LocalServer(name=s_data["name"], data=s_data)
            await do_local_server(new_serv)
            Globals.servers[s_data["name"]] = new_serv
    for unused_server in unused:
        log(INFO, f"SM; removing unused server {unused_server}")
        del Globals.servers[unused_server]


async def do_local_server(server: LocalServer):
    async def do_local_server_usage(closed=False):
        if closed:
            if await server.ram_usage is not None or await server.cpu_usage is not None:
                await server.update_usage(None, None)
            if await server.player_count is not None or await server.max_player_count is not None or await server.players:
                await server.update_players(None, None, [])
            return
        await server.update_usage(*await server.get_server_usage())
        await server.update_players(*await server.get_players())
        
    server_health = await server.is_server_healthy(tries=3)  # better be safe than sorry
    if time.monotonic() - server._data_updated > 3:
        server._data_updated = 0  # Force database update
    status = await server.status
    if server_health:
        if status == Status.CLOSING:
            if time.time() - (await server.status_updated_at) < SERVER_STOP_TIMEOUT: return
            log(WARNING, f"SM; Possible failed server closing for `{server.name}`")
        await do_local_server_usage()
        if await server.player_count == 0:
            if status != Status.RUNNING:
                await server.set_status(Status.RUNNING)
                return 
            if time.time() - (await server.status_updated_at) > await server.close_time:
                log(QINFO, f"SM; Autoclosing server {server.name}")
                task = asyncio.create_task(server.stop())
                stop_tasks.add(task)
                task.add_done_callback(stop_tasks.discard)
        else:
            await server.set_status(Status.RUNNING)

    else:
        if status == Status.STARTING:
            if time.time() - (await server.status_updated_at) < SERVER_START_TIMEOUT: return
            log(WARNING, f"SM; Possible failed server booting for `{server.name}`")
        if status == Status.CLOSING and not await server.is_server_closed():
            if time.time() - (await server.status_updated_at) < SERVER_STOP_TIMEOUT: return
            server.currently_closing = False
            log(WARNING, f"SM; Possible buggy after server closing for `{server.name}`")

        if server.is_screen_running():
            if status in [Status.CLOSED, Status.CLOSING]:
                log(WARNING, f"SM; Screen cleanup after `{server.name}`")
            else:
                log(ERROR, f"SM; Screen cleanup after active server `{server.name}`, possible crash.")
            server.quit_screen()
        if await server.is_java_running():
            if status in [Status.CLOSED, Status.CLOSING]:
                log(WARNING, f"SM; Java cleanup after `{server.name}`")
            else:
                log(ERROR, f"SM; Java cleanup after active server `{server.name}`, possible crash.")
            await server.kill_java()
        await server.set_status(Status.CLOSED)
        await do_local_server_usage(closed=True)


def api_thread():
    log(INFO, "- STARTING API HANDLER -")
    with ThreadingHTTPServer(("0.0.0.0", API_PORT), APIHandler) as server:
        server.seen_nonce = {}
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log(INFO, "server KeyboardInterrupt")
        log(INFO, "closing server")
        server.shutdown()
        server.server_close()


async def main():
    log(INFO, "- STARTING API HANDLER -")
    with ThreadingHTTPServer(("0.0.0.0", API_PORT), APIHandler) as server:
        server.seen_nonce = {}
        server.loop = asyncio.get_running_loop()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            log(INFO, "Loading servers...")
            await load_servers()
            log(INFO, "Servers loaded, starting main loop")
            next_run = time.monotonic()
            while True:
                next_run += LOOP_REFRESH
                try:
                    await asyncio.gather(*[
                        do_local_server(server)
                        for server in Globals.servers.values()
                    ])
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    log(ERROR, "SM; error in update loop; "+"\n".join(format_traceback(e)))

                delay = max(0, next_run - time.monotonic())
                await asyncio.sleep(delay)

        finally:
            log(INFO, "closing api server")
            await asyncio.to_thread(server.shutdown)
            await asyncio.to_thread(thread.join)



try:
    asyncio.run(main())
except KeyboardInterrupt:
    log(INFO, "KeyboardInterrupt, exiting.")
