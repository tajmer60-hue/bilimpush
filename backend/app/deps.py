"""Зависимости: получение текущего пользователя из JWT."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется авторизация")
    payload = decode_token(cred.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Токен недействителен")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нужны права администратора")
    return user


def get_optional_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                      db: Session = Depends(get_db)) -> User | None:
    if cred is None:
        return None
    payload = decode_token(cred.credentials)
    if not payload:
        return None
    return db.get(User, int(payload["sub"]))
