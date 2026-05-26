from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.api.schemas import TokenData
from src.config import get_settings

_bearer = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> TokenData:
    settings = get_settings()
    try:
        payload: dict[str, object] = jwt.decode(
            credentials.credentials,
            settings.api.secret_key,
            algorithms=[settings.api.jwt_algorithm],
        )
        sub = str(payload.get("sub", ""))
        tenant_id = str(payload.get("tenant_id", ""))
        if not sub or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing required claims",
            )
        return TokenData(sub=sub, tenant_id=tenant_id)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
