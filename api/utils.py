from dataclasses import dataclass
from typing import Callable, Dict, Literal
import json
import time
from http.client import HTTPMessage


@dataclass
class APIReturn:
    result: dict
    code: int = 200


@dataclass
class APIFunc:
    func: Callable[[HTTPMessage, dict[str, list[str]], ...], APIReturn]
    autoauth: bool | set


def api_get_json(headers: dict, body: bytes) -> dict | str | int | bool | None:
    ctype = headers.get("Content-Type", "")
    if ctype != "application/json":
        return None

    if not body:
        return None

    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return None


MISSING = object()

def read_dict(read: dict, read_elements: list) -> tuple[APIReturn | Literal[True], ...]:
    values = [None] * len(read_elements)
    if not isinstance(read, dict):
        return (APIReturn({"error": "body_not_json"}, 400), *values)
    for i, element in enumerate(read_elements):
        readed = read.get(element, MISSING)
        if readed is MISSING:
            return (APIReturn(
                {"error": {"missing value": element}}, 400),
                *values)
        values[i] = readed
    return (True, *values)


NONCE_TTL = 300

def cleanup_seen_nonces(seen_nonce: Dict[object, int]):
    now = time.time()
    for nonce_key, seen_at in list(seen_nonce.items()):
        if now - seen_at > NONCE_TTL:
            del seen_nonce[nonce_key]
