import fastapi
import uvicorn
from dotenv import load_dotenv


from src.__init__ import __version__

load_dotenv()

# Initialize the FastAPI application with its metadata
app = fastapi.FastAPI(
    title="Kompagnon - Algorithm API",
    description="API for the matching algorithm",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Import routes from src.api.routes
from src.api.routes import router as api_router

# Attach the router to the main application
app.include_router(api_router, prefix="/api")