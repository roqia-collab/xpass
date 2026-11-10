import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.api.deps import CurrentPrincipal, DbSession
from app.core.config import get_settings
from app.core.security import issue_dev_token
from app.modules.identity.service import describe_memberships, find_demo_user

router = APIRouter(tags=["identité"])


class DevLoginIn(BaseModel):
    email: EmailStr


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MembershipOut(BaseModel):
    scope_type: str
    scope_id: uuid.UUID | None
    scope_name: str
    role: str


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_demo: bool
    locale: str
    notify_email: bool
    # Vrai pour un compte relié au fournisseur d'identité (adresse e-mail vérifiée par celui-ci).
    email_verified: bool
    memberships: list[MembershipOut]


@router.post("/auth/dev/login", response_model=TokenOut)
def dev_login(body: DevLoginIn, db: DbSession) -> TokenOut:
    """Connexion de DÉVELOPPEMENT sans mot de passe, limitée aux comptes de démonstration.

    Répond 404 lorsque la fonctionnalité est désactivée (production, ou drapeau absent).
    """
    if not get_settings().dev_login_available:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "not_found", "message": "Introuvable."})
    user = find_demo_user(db, body.email)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, {"code": "unknown_demo_user", "message": "Compte de démonstration inconnu."}
        )
    token, ttl = issue_dev_token(str(user.id))
    return TokenOut(access_token=token, expires_in=ttl)


@router.get("/me", response_model=MeOut)
def me(principal: CurrentPrincipal, db: DbSession) -> MeOut:
    u = principal.user
    return MeOut(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        is_demo=u.is_demo,
        locale=u.locale,
        notify_email=u.notify_email,
        email_verified=u.oidc_subject is not None,
        memberships=[MembershipOut(**m) for m in describe_memberships(db, u.memberships)],
    )
