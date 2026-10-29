from pathlib import Path

from core.datatypes import LogType

DIR = Path(__file__).parent.resolve()

LOOP_REFRESH = 15

PRIVKEY_DIR = DIR/"priv_key.pem"
DATABASE_API = "https://minecraft.loleczkowo.com/database"
AUTH_MAP_LINK = "https://minecraft.loleczkowo.com/auth_map.json"
API_SERVICE = "server-rlifeart"
NODE_NAME = "server-rlifeart"


API_PORT = 35053
HONEYPOTS_DIR = DIR / "api" / "honeypots"

DEFAULT_SERVER_PATH = "/home/loleczkowo/mcdc/servers/{name}"
DEFAULT_START_COMMAND = "java -Xms{ram_min_mb}M -Xmx{ram_max_mb}M -jar server.jar"
SERVER_STOP_TIMEOUT = 180
SERVER_START_TIMEOUT = 180

LOG_DIR = DIR/"logs"
LOG_RETENTION_DAYS = 3
LOG_TO_CONSOLE = True
LOG_TIME_FORMAT = "%H:%M:%S"

DEBUG      = LogType("DEBUG")
QINFO      = LogType("Qinfo", to_console=False)  # quiet-log.
INFO       = LogType("INFO")
SUCCESS    = LogType("SUCCESS")
USER_INPUT = LogType("USERINP", to_console=False)
RESPONSE   = LogType("RESPONSE")  # aka console commmand response
WARNING    = LogType("WARNING")
ERROR      = LogType("ERROR")
CRITICAL   = LogType("CRITICAL")
ALL_LOG_TYPES = [INFO, SUCCESS, USER_INPUT, RESPONSE, WARNING, ERROR, CRITICAL]
