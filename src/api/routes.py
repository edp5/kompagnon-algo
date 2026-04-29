from fastapi import APIRouter

router = APIRouter()

# 2. We use @router.get instead of @app.get
@router.get("/", tags=["Root"])
def root():
    """API root endpoint."""
    return {"message": "Welcome to the Kompagnon Matching Algorithm API!"}

@router.get("/status", tags=["Status"])
def status():
    """API status endpoint."""
    return {"status": "ok" if True else "API is down: {error.message}"}