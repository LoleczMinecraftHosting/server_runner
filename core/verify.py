import hashlib
import time
import uuid
from typing import Dict, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


MAX_SKEW_SECONDS = 60


def make_signature_headers(private_key: Ed25519PrivateKey, method: str, path: str, body_bytes: bytes) -> Tuple[Dict[str, str], str]:
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    body_hash = hashlib.sha256(body_bytes).hexdigest()

    challenge = "##".join([str(timestamp), nonce, method.upper(), path, body_hash]).encode()

    signature = private_key.sign(challenge).hex()

    return {
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }, nonce


def verify_signature(public_key: Ed25519PublicKey, method: str, path: str, body_bytes: bytes, headers: dict, seen_nonce: Dict[object, int]):
    nonce = headers.get("X-Nonce", "")
    try:
        signature = bytes.fromhex(headers.get("X-Signature", ""))
    except ValueError:
        return False
    timestamp = int(headers.get("X-Timestamp", 0))

    now = int(time.time())
    if now - MAX_SKEW_SECONDS > timestamp:
        return False
    if timestamp > now + 5:
        return False

    nonce_key = f"{timestamp}:{nonce}"
    if nonce_key in seen_nonce:
        return False

    body_hash = hashlib.sha256(body_bytes).hexdigest()
    challenge = "##".join([str(timestamp), nonce, method.upper(), path, body_hash]).encode()

    try:
        public_key.verify(signature, challenge)
    except InvalidSignature:
        return False

    seen_nonce[nonce_key] = now
    return True


# RESPONSE


def make_response_signature_headers(private_key: Ed25519PrivateKey, request_headers: dict, status_code: int, response_body: bytes) -> Dict[str, str]:
    request_nonce = request_headers.get("X-Nonce", "")
    response_body_hash = hashlib.sha256(response_body).hexdigest()
    challenge = "##".join([request_nonce, str(status_code), response_body_hash]).encode()
    signature = private_key.sign(challenge).hex()
    return {"X-Resp-Signature": signature}


def verify_response_signature(public_key: Ed25519PublicKey, status_code: int, body_bytes: bytes, headers: dict, nonce: str):
    try:
        signature = bytes.fromhex(headers.get("X-Resp-Signature", ""))
    except ValueError:
        return False
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    challenge = "##".join([nonce, str(status_code), body_hash]).encode()
    try:
        public_key.verify(signature, challenge)
    except InvalidSignature:
        return False
    return True


# UTILS


def load_private_key(path):
    with open(path, "rb") as file:
        return serialization.load_pem_private_key(file.read(), password=None)


def load_auth_map(raw_auth_map: dict):
    auth_map = {}
    for service, public_key_pem in raw_auth_map.items():
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(public_key, Ed25519PublicKey):
            raise TypeError(f"{service} key is not an Ed25519 public key")
        auth_map[service] = public_key
    return auth_map
