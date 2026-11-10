"""Photos envoyées par les commerçants : contrôlées, réencodées en JPEG (métadonnées EXIF retirées), redimensionnées."""
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.core.storage import s3_client

MAX_BYTES = 8 * 1024 * 1024
MAX_SIDE = 1600
MIN_SIDE = 400
ALLOWED = {"JPEG", "PNG", "WEBP"}
Image.MAX_IMAGE_PIXELS = 40_000_000  # protège contre les images démesurées


class PhotoError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def prepare(data: bytes) -> bytes:
    if len(data) > MAX_BYTES:
        raise PhotoError("too_large", "Photo trop lourde (8 Mo maximum).")
    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise PhotoError("invalid_image", "Fichier illisible : envoyez une photo JPEG, PNG ou WebP.") from exc
    if fmt not in ALLOWED:
        raise PhotoError("invalid_image", "Format non accepté : JPEG, PNG ou WebP.")
    img = ImageOps.exif_transpose(img).convert("RGB")
    if min(img.size) < MIN_SIDE:
        raise PhotoError("too_small", f"Photo trop petite ({MIN_SIDE} pixels minimum de côté).")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85, optimize=True)  # nouvelle image : aucune métadonnée d'origine
    return out.getvalue()


def store(key: str, jpeg: bytes) -> None:
    s3_client().put_object(Bucket=get_settings().s3_public_bucket, Key=key, Body=jpeg, ContentType="image/jpeg",
                           CacheControl="public, max-age=31536000, immutable")
