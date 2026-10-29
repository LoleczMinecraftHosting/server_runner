import asyncio
from traceback import format_exception


def traceback_lines(error) -> list[str]:
    tblines = format_exception(error)
    return [ln for line in tblines for ln in line.rstrip().split("\n")]


def format_traceback(error) -> list[str]:
    lines = traceback_lines(error)
    formatted_lines: list[str] = [lines[0]]
    for line in lines[1:]:
        stripped = line.strip()
        if stripped.startswith("File"):
            parts = stripped.split(", ")
            tmp = parts[0].split(" ")
            tmp[0] = "File"
            parts[0] = " ".join(tmp)
            if len(parts) >= 3:
                parts[2] = f"in {parts[2].split()[1]}"
            formatted_lines.append(", ".join(parts))
        elif stripped and all(c in "^~" for c in stripped):
            formatted_lines.append(line)
        elif ":" in line and line[0] != " " and len(line.split(":")) > 1:
            formatted_lines.append(line)
        else:
            formatted_lines.append(line)
    for i in range(1, len(formatted_lines)):
        formatted_lines[i] = f">{formatted_lines[i]}"
    return formatted_lines


def format_time(seconds: float):
    minutes = seconds//60
    seconds = int(seconds-minutes*60)
    hours = int(minutes//60)
    minutes = int(minutes-hours*60)
    text = ""
    if hours > 0:
        text += str(hours)+" hour"+"s"*(hours > 1)+" "
    if minutes > 0:
        text += str(minutes)+" minute"+"s"*(minutes > 1)+" "
    if text != "":
        text += "and "
    text += str(seconds)+" second"+"s"*(not seconds == 1)
    return text

async def network_working(host="1.1.1.1", timeout=3):
    proc = await asyncio.create_subprocess_exec(
        "ping", "-c", "1", "-W", str(timeout), host,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout)
        return proc.returncode == 0
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False
