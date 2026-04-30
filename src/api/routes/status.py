from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import src.db.session as session
import src.db.models as models

router = APIRouter()

@router.get("/status", tags=["Status"], description="API status endpoint")
def status(db: Session = Depends(session.get_db)):
    """API status endpoint."""
    try:
        db.execute(models.sa.text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"down: {str(e)}"

    return {"status": "ok", "db_status": db_status}
