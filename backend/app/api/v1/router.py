from fastapi import APIRouter

from app.api.v1 import api_keys, crowding, members, orgs, routes, trips

router = APIRouter(prefix="/api/v1")
router.include_router(orgs.router)
router.include_router(members.router)
router.include_router(api_keys.router)
router.include_router(routes.router)
router.include_router(trips.router)
router.include_router(crowding.router)
