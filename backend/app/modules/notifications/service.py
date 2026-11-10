"""E-mails transactionnels, envoyés APRÈS commit à partir de l'outbox (rejouables).

- Aucun e-mail si SMTP n'est pas configuré (l'événement est simplement marqué diffusé).
- Respect des préférences : un client qui a désactivé les e-mails n'en reçoit pas, sauf ceux liés à une
  démarche qu'il a lui-même engagée (réponse à sa demande d'assistance, décision sur sa réclamation).
- Un échec SMTP laisse l'événement en file : il est retenté (10 tentatives maximum).
- Les e-mails ne contiennent jamais de jeton QR, de code ni de lien de connexion.
"""
import logging
import smtplib
import uuid
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import make_msgid
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.booking.models import Booking
from app.modules.catalog.models import Location, Market, Merchant, OfferVersion
from app.modules.identity.models import Organization, User
from app.modules.platform.models import OutboxEvent

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 10
ROLE_LABELS = {"merchant_owner": "responsable", "merchant_staff": "équipe",
               "hr_admin": "administrateur RH", "hr_viewer": "lecture seule"}


@dataclass
class Mail:
    to: str
    subject: str
    body: str


def send(mail: Mail) -> None:
    s = get_settings()
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.mail_from, mail.to, mail.subject
    msg["Message-ID"] = make_msgid(domain="xpass.local")
    msg.set_content(mail.body + "\n\n— L'équipe XPASS\nCet e-mail est envoyé automatiquement, merci de ne pas y répondre.\n")
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
        if s.smtp_starttls:
            smtp.starttls()
        if s.smtp_username:
            smtp.login(s.smtp_username, s.smtp_password)
        smtp.send_message(msg)


def _recipient(user: User | None, *, transactional_only: bool) -> str | None:
    if user is None or not user.is_active or user.deleted_at is not None:
        return None
    if transactional_only and not user.notify_email:
        return None
    return user.email


def _booking_context(db: Session, booking_id: uuid.UUID):
    b = db.get(Booking, booking_id)
    if b is None:
        return None
    loc = db.get(Location, b.location_id)
    tz = db.scalar(select(Market.timezone).join(Merchant, Merchant.market_id == Market.id).where(Merchant.id == loc.merchant_id))
    title = db.scalar(select(OfferVersion.title).where(OfferVersion.id == b.offer_version_id))
    when = b.starts_at.astimezone(ZoneInfo(tz)).strftime("%d/%m/%Y à %H:%M")
    return b, loc, title, when


def build(db: Session, event: OutboxEvent) -> Mail | None:
    """Construit l'e-mail correspondant à un événement, ou None s'il n'y a rien à envoyer."""
    p, t = event.payload or {}, event.event_type
    if t == "booking.reminder":
        ctx = _booking_context(db, event.aggregate_id)
        if ctx is None:
            return None
        b, loc, title, when = ctx
        to = _recipient(db.get(User, b.user_id), transactional_only=True)
        if to is None or b.status != "confirmed":
            return None
        return Mail(to, f"C'est demain · {loc.name}",
                    f"Rappel : « {title} » chez {loc.name} le {when}.\nAdresse : {loc.address_line}, {loc.postal_code}.\n"
                    "Présentez votre QR code depuis l'application. Besoin d'annuler ? Faites-le depuis l'application.")
    if t == "message.posted":
        from app.modules.engagement.models import Conversation

        conv = db.get(Conversation, event.aggregate_id)
        if conv is None:
            return None
        loc = db.get(Location, conv.location_id)
        if p.get("sender_kind") == "partner":
            to = _recipient(db.get(User, conv.customer_id), transactional_only=False)
            return None if to is None else Mail(
                to, f"Nouveau message de {loc.name}",
                f"{loc.name} vous a écrit au sujet de votre réservation. Ouvrez l'application XPASS pour lire et répondre.")
        return None  # côté établissement : notification dans le portail (pas d'e-mail à chaque message)
    if t in ("booking.confirmed", "booking.cancelled", "booking.redeemed"):
        ctx = _booking_context(db, event.aggregate_id)
        if ctx is None:
            return None
        b, loc, title, when = ctx
        to = _recipient(db.get(User, b.user_id), transactional_only=True)
        if to is None:
            return None
        if t == "booking.confirmed":
            return Mail(to, f"Réservation confirmée · {loc.name}",
                        f"Votre réservation « {title} » chez {loc.name} le {when} est confirmée.\n"
                        f"{b.total_credits} crédits sont réservés. Présentez votre QR depuis l'application le jour J.")
        if t == "booking.cancelled":
            late = p.get("late")
            return Mail(to, f"Réservation annulée · {loc.name}",
                        f"Votre réservation « {title} » du {when} est annulée.\n"
                        + (f"Annulation tardive : {b.total_credits} crédits ont été débités." if late
                           else f"Vos {b.total_credits} crédits vous ont été restitués."))
        return Mail(to, f"Votre reçu {p.get('receipt', '')} · {loc.name}",
                    f"Merci pour votre visite chez {loc.name} ({title}).\n{p.get('credits')} crédits ont été utilisés. "
                    f"Référence du reçu : {p.get('receipt')}.")
    if t in ("dispute.refunded", "dispute.rejected"):
        from app.modules.ops.models import Dispute

        d = db.get(Dispute, event.aggregate_id)
        b = db.get(Booking, d.booking_id) if d else None
        to = _recipient(db.get(User, b.user_id) if b else None, transactional_only=False)
        if to is None:
            return None
        if t == "dispute.refunded":
            return Mail(to, f"Réclamation {d.reference} : crédits restitués",
                        f"Votre réclamation {d.reference} a été acceptée : {d.credits_restored} crédits vous ont été restitués.")
        return Mail(to, f"Réclamation {d.reference} : décision",
                    f"Votre réclamation {d.reference} n'a pas été retenue.\nMotif : {d.resolution_reason}")
    if t == "support.answered":
        from app.modules.ops.models import SupportRequest

        r = db.get(SupportRequest, event.aggregate_id)
        to = _recipient(db.get(User, r.user_id) if r else None, transactional_only=False)
        if to is None:
            return None
        return Mail(to, f"Réponse à votre demande {r.reference}",
                    f"Votre demande « {r.subject} » a reçu une réponse :\n\n{r.reply}")
    if t == "location.change_decided":
        from app.modules.catalog.models import LocationChangeRequest

        r = db.get(LocationChangeRequest, event.aggregate_id)
        to = _recipient(db.get(User, r.requested_by) if r else None, transactional_only=False)
        if r is None or to is None:
            return None
        loc = db.get(Location, r.location_id)
        if r.status == "approved":
            return Mail(to, f"Modification acceptée · {loc.name}",
                        f"Votre demande de modification de « {loc.name} » a été acceptée et appliquée à la fiche.")
        return Mail(to, f"Modification refusée · {loc.name}",
                    f"Votre demande de modification de « {loc.name} » n'a pas été retenue.\nMotif : {r.decision_reason}")
    if t == "merchant.applied":
        m = db.get(Merchant, event.aggregate_id)
        to = _recipient(db.get(User, uuid.UUID(p["user_id"])) if p.get("user_id") else None, transactional_only=False)
        if m is None or to is None:
            return None
        return Mail(to, "Votre candidature XPASS est bien reçue",
                    f"Bonjour,\n\nNous avons bien reçu la candidature de {m.display_name} ({p.get('location')}).\n"
                    "L'équipe XPASS vérifie votre dossier. En attendant, vous pouvez compléter votre établissement "
                    "depuis le portail commerçant : photos, prestations, horaires et équipe.\n"
                    "Votre établissement sera visible des clients après validation.")
    if t == "access.granted":
        from app.modules.identity.models import Membership

        m = db.get(Membership, event.aggregate_id)
        to = _recipient(db.get(User, m.user_id) if m else None, transactional_only=False)
        if to is None:
            return None
        space = "commerçant" if p.get("scope_type") == "merchant" else "entreprise"
        return Mail(to, f"Votre accès à l'espace {space} XPASS",
                    f"Bonjour,\n\n{p.get('by_name') or 'L’équipe XPASS'} vous a donné accès à l'espace {space} de {p.get('scope_label')} "
                    f"({ROLE_LABELS.get(p.get('role'), p.get('role'))}).\n"
                    "Ouvrez le portail professionnel XPASS et connectez-vous avec cette adresse e-mail. "
                    "Si vous n'avez pas encore de compte, choisissez « Créer un compte » avec cette même adresse.")
    if t == "employee.invited":
        from app.modules.employer.models import Employee

        e = db.get(Employee, event.aggregate_id)
        if e is None or e.status != "invited" or e.is_demo:
            return None
        org = db.get(Organization, e.organization_id)
        return Mail(e.email, f"{org.name} vous offre l'avantage XPASS",
                    f"Bonjour {e.first_name},\n\n{org.name} vous invite à profiter de crédits XPASS pour des activités "
                    "bien-être, sport, culture et loisirs.\nInstallez l'application XPASS, connectez-vous avec cette "
                    "adresse e-mail puis acceptez l'invitation depuis votre Profil.\n"
                    "Votre employeur ne voit pas le détail de vos réservations.")
    return None


def deliver(db: Session, event: OutboxEvent) -> None:
    """Envoie l'e-mail puis la notification liés à l'événement ; lève une exception en cas d'échec (retenté)."""
    from app.modules.notifications import push

    if get_settings().smtp_host:
        mail = build(db, event)
        if mail is not None:
            send(mail)
            log.info("e-mail %s envoyé (%s)", event.event_type, event.id)
    if push.configured() and push.deliver(db, event):
        log.info("notification %s envoyée (%s)", event.event_type, event.id)
