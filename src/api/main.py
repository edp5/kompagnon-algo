import fastapi
import uvicorn

# Initialize the FastAPI application with its metadata
app = fastapi.FastAPI(
    title="Kompagnon Matching Algorithm API",
    description="API for the matching algorithm",
    version="0.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Import routes from src.api.routes
from src.api.routes import router as api_router

# Attach the router to the main application
app.include_router(api_router)