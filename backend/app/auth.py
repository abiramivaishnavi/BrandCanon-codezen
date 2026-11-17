"""JWT login + role-based access control (RBAC)."""
import hashlib, hmac, os
from datetime import datetime, timedelta
import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .config import JWT_SECRET, JWT_HOURS
from .db import get_db
from .models import User


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 120_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


def make_token(user: User) -> str:
    payload = {"sub": str(user.id), "role": user.role, "exp": datetime.utcnow() + timedelta(hours=JWT_HOURS)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Not logged in")
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired, please log in again")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(401, "User not found")
    return user


def require(*roles: str):
    """Dependency factory: require(\"admin\") only lets admins through."""
    def checker(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, f"This action needs one of these roles: {', '.join(roles)}")
        return user
    return checker
