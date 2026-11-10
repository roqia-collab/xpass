"""Notifications sur téléphone via Firebase Cloud Messaging (API HTTP v1).

Configuration : `FCM_SERVICE_ACCOUNT_FILE` = fichier JSON du compte de service Firebase (projet à votre nom).
Sans ce fichier, rien n'est envoyé (aucun faux envoi) : les e-mails restent le canal de secours.
Le contenu reste neutre : jamais de code, de QR ni de lien de connexion dans une notification.
"""
import json
import logging
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.booking.models import Booking
from app.modules.catalog.models import Location
from app.modules.engagement.models import Conversation, PushDevice
from app.modules.identity.models import Membership, User
from app.modules.platform.models import OutboxEvent

log = logging.getLogger(__name__)
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


@dataclass
class Push:
    user_ids: list[uuid.UUID]
    title: str
    body: str
    route: str  # écran de l'application à ouvrir (ex. « /reservations/<id> »)


@lru_cache
def _account() -> dict | None:
    path = get_settings().fcm_service_account_file
    if not path:
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


_token: dict = {"value": None, "exp": 0}


def _access_token(account: dict) -> str:
    """Jeton OAuth2 du compte de service (assertion JWT signée RS256), mis en cache ~55 minutes."""
    if _token["value"] and _token["exp"] > time.time() + 60:
        return _token["value"]
    now = int(time.time())
    assertion = jwt.encode({"iss": account["client_email"], "scope": SCOPE, "aud": account["token_uri"],
                            "iat": now, "exp": now + 3600}, account["private_key"], algorithm="RS256")
    r = httpx.post(account["token_uri"], data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                               "assertion": assertion}, timeout=10)
    r.raise_for_status()
    data = r.json()
    _token.update(value=data["access_token"], exp=now + int(data.get("expires_in", 3600)))
    return _token["value"]


def configured() -> bool:
    return _account() is not None


def build(db: Session, event: OutboxEvent) -> Push | None:
    t, p = event.event_type, event.payload or {}
    if t in ("booking.confirmed", "booking.cancelled", "booking.reminder"):
        b = db.get(Booking, event.aggregate_id)
        if b is None:
            return None
        loc = db.get(Location, b.location_id)
        title = {"booking.confirmed": "Réservation confirmée", "booking.cancelled": "Réservation annulée",
                 "booking.reminder": "C'est demain !"}[t]
        body = {"booking.confirmed": f"{loc.name} : votre réservation est confirmée.",
                "booking.cancelled": f"{loc.name} : votre réservation est annulée.",
                "booking.reminder": f"Rendez-vous chez {loc.name}. Votre QR code est dans l'application."}[t]
        return Push([b.user_id], title, body, f"/reservations/{b.id}")
    if t == "message.posted":
        conv = db.get(Conversation, event.aggregate_id)
        if conv is None:
            return None
        loc = db.get(Location, conv.location_id)
        if p.get("sender_kind") == "partner":
            return Push([conv.customer_id], f"Message de {loc.name}", "Vous avez reçu un message au sujet de votre réservation.",
                        f"/reservations/{conv.booking_id}/messages")
        owners = db.scalars(select(Membership.user_id).where(Membership.scope_type == "merchant",
                                                             Membership.scope_id == loc.merchant_id)).all()
        return Push(list(owners), "Nouveau message client", f"Un client vous a écrit ({loc.name}).", "/partner/messages")
    return None


def deliver(db: Session, event: OutboxEvent) -> int:
    """Envoie la notification liée à l'événement ; retire les jetons que Firebase déclare invalides."""
    account = _account()
    if account is None:
        return 0
    push = build(db, event)
    if push is None:
        return 0
    devices = db.scalars(select(PushDevice).join(User, User.id == PushDevice.user_id)
                         .where(PushDevice.user_id.in_(push.user_ids), User.is_active.is_(True))).all()
    if not devices:
        return 0
    url = f"https://fcm.googleapis.com/v1/projects/{account['project_id']}/messages:send"
    headers = {"Authorization": f"Bearer {_access_token(account)}"}
    sent = 0
    for d in devices:
        msg = {"message": {"token": d.token, "notification": {"title": push.title, "body": push.body},
                           "data": {"route": push.route}}}
        r = httpx.post(url, json=msg, headers=headers, timeout=10)
        if r.status_code == 200:
            sent += 1
        elif r.status_code in (400, 404) and ("UNREGISTERED" in r.text or "INVALID_ARGUMENT" in r.text):
            db.delete(d)  # jeton périmé : l'application le réenregistrera à la prochaine ouverture
        else:
            r.raise_for_status()  # erreur temporaire : l'événement reste en file et sera retenté
    return sent
