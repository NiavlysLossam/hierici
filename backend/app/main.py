import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.config import settings
from app.core.database import check_db_connection, engine
from app.core.init_db import init_db
from app.core.territory import TerritoryMiddleware
from app.api.v1 import api_v1_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialisation de la base de données et du territoire par défaut
    logger.info("Démarrage de l'API HierIci...")
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la BDD : {e}")
    yield
    # Shutdown: fermeture propre des connexions
    logger.info("Arrêt de l'API HierIci...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API REST & Géospatiale pour la plateforme HierIci",
    version="0.1.0",
    lifespan=lifespan,
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Middleware de contexte territorial multi-tenant
app.add_middleware(TerritoryMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enveloppe standardisée RFC 7807 Problem Details pour les erreurs de validation de schéma."""
    encoded_errors = jsonable_encoder(exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "type": "https://hierici.local/errors/unprocessable_entity",
            "title": "UNPROCESSABLE_ENTITY",
            "status": 422,
            "detail": encoded_errors,
            "instance": str(request.url.path),
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Erreur de validation des données transmises.",
                "details": encoded_errors,
            },
        },
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Enveloppe standardisée RFC 7807 Problem Details pour les erreurs HTTP de l'API."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        error_info = exc.detail["error"]
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://hierici.local/errors/{error_info.get('code', 'HTTP_ERROR').lower()}",
                "title": error_info.get("code", "HTTP_ERROR"),
                "status": exc.status_code,
                "detail": error_info.get("message", ""),
                "instance": str(request.url.path),
                "error": error_info,
            },
            headers=getattr(exc, "headers", None),
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )

# Inclusion des routes v1
app.include_router(api_v1_router)

# Montage du stockage local pour servir les médias statiques
if settings.STORAGE_DRIVER == "local":
    upload_path = Path(settings.LOCAL_STORAGE_PATH)
    upload_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")



@app.get("/api/health", tags=["Système"])
async def health_check():
    """Vérification de l'état de l'API et de la connexion à la base de données."""
    is_db_connected = await check_db_connection()
    if is_db_connected:
        return {
            "status": "ok",
            "database": "connected",
            "environment": settings.ENVIRONMENT,
            "default_territory": settings.DEFAULT_TERRITORY_SLUG,
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "database": "disconnected",
                "environment": settings.ENVIRONMENT,
            },
        )


@app.get("/", tags=["Racine"])
async def root():
    return {
        "message": f"Bienvenue sur l'API {settings.PROJECT_NAME}",
        "docs_url": "/docs",
        "health_check": "/api/health",
        "territory_current": "/api/v1/territory/current",
    }
