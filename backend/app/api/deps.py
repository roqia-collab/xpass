from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import InvalidToken, verify_token
from app.db.session import get_db
from app.modules.identity.service import Principal, resolve_principal

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthorized", "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_principal(db: DbSession, authorization: Annotated[str | None, Header()] = None) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized("Authentification requise.")
    try:
        claims = verify_token(authorization.split(" ", 1)[1].strip())
    except InvalidToken as exc:
        raise _unauthorized(str(exc)) from exc
    principal = resolve_principal(db, claims)
    if principal is None:
        raise _unauthorized("Compte inconnu ou désactivé.")
    return principal


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]


def forbidden(message: str = "Accès refusé pour ce rôle.") -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "forbidden", "message": message})
