import re

from config import HONEYPOTS_DIR
from urllib.parse import unquote

# regex, filename, content_type
HONEYPOTS = [
        (
        re.compile(r"(?:^|/)\.env(?:\.[a-z0-9_-]+)*(?=/|$)", re.I),
        ".env",
        "text/plain"
    ),
    (
        re.compile(r"(?:^|/)auth\.json(?:\.[a-z0-9_-]+)*(?=/|$)", re.I),
        "auth.json",
        "application/json"
    ),
    (
        re.compile(r"(?:^|/)schema\.rb(?:\.[a-z0-9_-]+)*(?=/|$)", re.I),
        "schema.rb",
        "text/plain"
    ),
]


def get_honeypot(path):
    for _ in range(3):
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    path = path.replace("\\", "/")
    for regex, filename, content_type in HONEYPOTS:
        if regex.search(path):
            file = HONEYPOTS_DIR / filename
            return content_type, file.read_bytes()
    return None
