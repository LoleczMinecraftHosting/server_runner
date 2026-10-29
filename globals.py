from __future__ import annotations
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.mc_server import LocalServer


class Globals:
    auth_map: dict[str, Ed25519PublicKey] | None = None
    priv_key: Ed25519PrivateKey | None = None

    servers: dict[str, LocalServer] = {}
