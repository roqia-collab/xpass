"""Point d'import unique de tous les modèles (utilisé par Alembic)."""
from app.db.base import Base
from app.modules.catalog import models as catalog_models  # noqa: F401
from app.modules.identity import models as identity_models  # noqa: F401
from app.modules.booking import models as booking_models  # noqa: F401
from app.modules.platform import models as platform_models  # noqa: F401
from app.modules.redemption import models as redemption_models  # noqa: F401
from app.modules.payments import models as payments_models  # noqa: F401
from app.modules.settlement import models as settlement_models  # noqa: F401
from app.modules.employer import models as employer_models  # noqa: F401
from app.modules.ops import models as ops_models  # noqa: F401
from app.modules.wallet import models as wallet_models  # noqa: F401

__all__ = ["Base"]
from app.modules.engagement import models as engagement_models  # noqa: F401
