import asyncio
from typing import Tuple

import psutil


async def get_cpu_usage():
    psutil.cpu_percent()
    await asyncio.sleep(1)
    return psutil.cpu_percent()


def get_ram_usage() -> Tuple[int, int]:
    usage = psutil.virtual_memory()
    return usage.total, usage.used


async def get_pid_usage(pid: int) -> Tuple[int, float]:
    root = psutil.Process(pid)
    procs = [root, *root.children(recursive=True)]
    for proc in procs:
        try:
            proc.cpu_percent()
        except psutil.Error:
            pass

    await asyncio.sleep(1)
    ram, cpu = 0, 0.0

    for proc in procs:
        try:
            ram += proc.memory_info().rss
            cpu += proc.cpu_percent()
        except psutil.Error:
            pass

    return ram, cpu / (psutil.cpu_count() or 1)


GIB = 1024 ** 3
MB = 1024 ** 2

def bytes_to_gib(bytes: int):
    return bytes/GIB
def bytes_to_mb(bytes: int):
    return bytes/MB
def mb_to_gib(mb: int):
    return mb/1024