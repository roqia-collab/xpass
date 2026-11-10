from fastapi import APIRouter

from app.api.v1 import account, admin, auth, bookings, catalog, company, engagement, partner_manage, partners, payments, portals, redemptions, settlements, wallet

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(catalog.router)
api_router.include_router(auth.router)
api_router.include_router(portals.router)
api_router.include_router(bookings.router)
api_router.include_router(wallet.router)
api_router.include_router(redemptions.router)
api_router.include_router(payments.router)
api_router.include_router(settlements.router)
api_router.include_router(partner_manage.router)
api_router.include_router(partners.router)
api_router.include_router(engagement.router)
api_router.include_router(company.router)
api_router.include_router(admin.router)
api_router.include_router(account.router)
