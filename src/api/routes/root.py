from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["Root"], description="API root endpoint")
def root():
    """API root endpoint."""
    return {"message": "Welcome to the Kompagnon Matching Algorithm API!"}
