"""Хеширование паролей (pbkdf2 из stdlib) и JWT-токены."""
import hashlib
import hmac
import os
import time

import jwt

SECRET_KEY = os.environ.get("BILIM_SECRET", "bilim-dev-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_TTL = 60 * 60 * 24 * 30  # 30 дней


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(check, digest)


def create_token(user_id: int, is_admin: bool = False) -> str:
    payload = {
        "sub": str(user_id),
        "admin": is_admin,
        "exp": int(time.time()) + TOKEN_TTL,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
