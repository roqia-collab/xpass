"""Dépose les médias PLACEHOLDER de démonstration dans le bucket public.

Usage : docker compose exec api python -m app.seed.media
"""
import mimetypes
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.storage import ensure_bucket, s3_client

SOURCE = Path("/srv/seed-media")
PREFIX = "demo"


def main() -> int:
    settings = get_settings()
    if not SOURCE.exists():
        print(f"Dossier {SOURCE} absent (monté par docker-compose).", file=sys.stderr)
        return 1
    ensure_bucket(settings.s3_public_bucket)
    ensure_bucket(settings.s3_private_bucket)
    client = s3_client()
    count = 0
    for path in sorted(SOURCE.rglob("*")):
        if path.is_file() and path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            key = f"{PREFIX}/{path.relative_to(SOURCE).as_posix()}"
            client.upload_file(
                str(path),
                settings.s3_public_bucket,
                key,
                ExtraArgs={"ContentType": mimetypes.guess_type(path.name)[0] or "application/octet-stream"},
            )
            count += 1
    print(f"{count} médias placeholder déposés dans {settings.s3_public_bucket}/{PREFIX}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
