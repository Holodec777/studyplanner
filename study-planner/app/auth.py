import base64
import binascii
import hashlib
import hmac
import json
import os
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

load_dotenv()
bearer = HTTPBearer(auto_error=False)
# shortcut: fixed development fallback for offline coursework demos, replace SECRET_KEY before network exposure.
SECRET_KEY = os.getenv("SECRET_KEY", "study-planner-local-secret-change-before-network-use").encode()
HASH_ITERATIONS = 260_000
TOKEN_TTL_SECONDS = 12 * 60 * 60


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, HASH_ITERATIONS)
    return f"pbkdf2_sha256${HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def create_access_token(user_id: int) -> str:
    payload = _b64(json.dumps({"sub": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}).encode())
    signature = _b64(hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def decode_access_token(token: str) -> int:
    try:
        payload, signature = token.split(".")
        expected = _b64(hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(data["exp"]) <= int(time.time()):
            raise ValueError("Expired token")
        return int(data["sub"])
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, binascii.Error) as exc:
        raise HTTPException(status_code=401, detail="Недействительный или истёкший токен", headers={"WWW-Authenticate": "Bearer"}) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Войдите в аккаунт", headers={"WWW-Authenticate": "Bearer"})
    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Аккаунт не найден или отключён", headers={"WWW-Authenticate": "Bearer"})
    return user
