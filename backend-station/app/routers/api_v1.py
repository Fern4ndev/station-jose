"""Version 1 API router."""

from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.catalogs import router as catalogs_router
from app.routers.health import router as health_router
from app.routers.purchase_orders import router as purchase_orders_router
from app.routers.users import router as users_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(catalogs_router)
router.include_router(purchase_orders_router)
router.include_router(users_router)
