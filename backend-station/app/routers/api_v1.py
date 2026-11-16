"""Version 1 API router."""

from fastapi import APIRouter

from app.routers.attendances import router as attendances_router
from app.routers.auth import router as auth_router
from app.routers.catalogs import router as catalogs_router
from app.routers.health import router as health_router
from app.routers.purchase_orders import router as purchase_orders_router
from app.routers.users import router as users_router
from app.routers.verifications import router as verifications_router
from app.routers.vouchers import router as vouchers_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(attendances_router)
router.include_router(catalogs_router)
router.include_router(purchase_orders_router)
router.include_router(users_router)
router.include_router(vouchers_router)
router.include_router(verifications_router)
