from fastapi import APIRouter

from src.api.routes.root import router as root_router
from src.api.routes.status import router as status_router
from src.api.routes.put_journey import router as put_journey_router
from src.api.routes.match import router as match_router

router = APIRouter()

# Attach each modular route to the main API router
router.include_router(root_router)
router.include_router(status_router)
router.include_router(put_journey_router)
router.include_router(match_router)