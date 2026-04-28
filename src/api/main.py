import fastapi
import uvicorn

# Initialisation de l'application FastAPI avec ses métadonnées
app = fastapi.FastAPI(
    title="API Algo Matching Kompagnon",
    description="API pour l'algorithme de matching",
    version="0.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Import des routes depuis src.api.routes
from src.api.routes import router as api_router

# On attache le router à notre application principale
app.include_router(api_router)