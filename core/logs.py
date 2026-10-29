import datetime
from time import gmtime, strftime
from config import LOG_DIR, LOG_RETENTION_DAYS, LOG_TO_CONSOLE, LOG_TIME_FORMAT, ALL_LOG_TYPES
from core.datatypes import LogType


_TYPE_WIDTH = max(len(t.name) for t in ALL_LOG_TYPES)
_WHITESPACE = " "*(_TYPE_WIDTH+len(strftime(LOG_TIME_FORMAT, gmtime()))+1)

LOG_DIR.mkdir(parents=True, exist_ok=True)


def _plain_log(log_text: str, log_type: LogType):
    if log_type.to_console and LOG_TO_CONSOLE:
        print(log_text)

    if not log_type.to_file:
        return

    today = datetime.date.today().isoformat()
    log_file = LOG_DIR / f"{today}.log"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(log_text + "\n")
    cutoff = datetime.datetime.now()-datetime.timedelta(days=LOG_RETENTION_DAYS)
    for path in LOG_DIR.glob("*.log"):
        try:
            date_str = path.stem
            file_date = datetime.datetime.fromisoformat(date_str)
        except Exception:
            continue
        if file_date < cutoff:
            path.unlink()


def get_logs(lines: int):
    today = datetime.date.today().isoformat()
    log_file = LOG_DIR / f"{today}.log"
    with open(log_file, "r", encoding="utf-8") as f:
        log_lines = f.readlines()
    return log_lines[-int(lines):]


def log(log_type: LogType, message: str, *args, join=""):
    message = message+join+join.join([str(a) for a in args])
    lines = message.split("\n")
    head = f"{strftime(LOG_TIME_FORMAT, gmtime())} {log_type.name.ljust(_TYPE_WIDTH)}"
    header = f"{head} || {lines[0]}"

    if len(lines) > 1:
        if log_type.newline_formatting:
            ind = _WHITESPACE+"  | "
            body = "\n".join(f"{ind}{lins}" for lins in lines[1:])
        else:
            body = "\n".join(lines[1:])
        _plain_log(f"{header}\n{body}", log_type)
    else:
        _plain_log(header, log_type)
