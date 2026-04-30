from fastapi import APIRouter

from src.api.routes.root import router as root_router
from src.api.routes.status import router as status_router
from src.api.routes.get_valid import router as get_valid_router
from src.api.routes.get_invalid import router as get_invalid_router
from src.api.routes.put_journey import router as put_journey_router

router = APIRouter()

# Attach each modular route to the main API router
router.include_router(root_router)
router.include_router(status_router)
router.include_router(get_valid_router)
router.include_router(get_invalid_router)
router.include_router(put_journey_router)