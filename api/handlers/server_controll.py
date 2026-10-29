import asyncio

from api.api_core import APIHandler
from api.utils import APIReturn, read_dict, api_get_json
from globals import Globals

@APIHandler.post("/server/{server_name}/start")
async def server_start(headers, query, data, server_name):
    if server_name not in Globals.servers:
        return APIReturn({"error": "server does not exist"}, code=404)
    await Globals.servers[server_name].start()
    return APIReturn({"status": "ok"})

@APIHandler.post("/server/{server_name}/stop")
async def server_stop(headers, query, data, server_name):
    if server_name not in Globals.servers:
        return APIReturn({"error": "server does not exist"}, code=404)
    await Globals.servers[server_name].stop()
    return APIReturn({"status": "ok"})

@APIHandler.post("/server/{server_name}/restart")
async def server_restart(headers, query, data, server_name):
    if server_name not in Globals.servers:
        return APIReturn({"error": "server does not exist"}, code=404)
    asyncio.create_task(Globals.servers[server_name].restart())
    return APIReturn({"status": "ok"})


@APIHandler.get("/server/{server_name}/properties")
async def server_properties(headers, query, server_name):
    if server_name not in Globals.servers:
        return APIReturn({"error": "server does not exist"}, code=404)
    return APIReturn(await Globals.servers[server_name].get_properties())
@APIHandler.post("/server/{server_name}/properties/{property}")
async def server_set_property(headers, query, data, server_name, property):
    if server_name not in Globals.servers:
        return APIReturn({"error": "server does not exist"}, code=404)
    new_value = api_get_json(headers, data)
    if not isinstance(new_value, str):
        return APIReturn({"error": "expected a string as data"}, code=400)
    return APIReturn(await Globals.servers[server_name].set_property(property, new_value))

@APIHandler.get("/server/{server_name}/console/{lines}")
async def server_get_console(headers, query, server_name, lines):
    if server_name not in Globals.servers:
        return APIReturn({"error": "server does not exist"}, code=404)
    try:
        lines = int(lines)
    except ValueError:
        return APIReturn({"error": "lines must be an int"}, code=400)
    return APIReturn(await Globals.servers[server_name].read_logs(lines))
@APIHandler.post("/server/{server_name}/console")
async def server_send_console(headers, query, data, server_name):
    if server_name not in Globals.servers:
        return APIReturn({"error": "server does not exist"}, code=404)
    command = api_get_json(headers, data)
    if not isinstance(command, str):
        return APIReturn({"error": "expected a string as data"}, code=400)
    return APIReturn(await Globals.servers[server_name].command(command))
