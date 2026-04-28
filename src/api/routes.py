from fastapi import APIRouter

router = APIRouter()

# 2. On utilise @router.get au lieu de @app.get
@router.get("/", tags=["Root"])
def root():
    """Point d'entrée de l'API."""
    return {"message": "Bienvenue sur l'API de matching de l'algorithme Kompagnon !"}

@router.get("/status", tags=["Status"])
def status():
    """Statut de l'API."""
    return {"status": "ok" if True else "L'API rencontre un problème : {error.message}"}