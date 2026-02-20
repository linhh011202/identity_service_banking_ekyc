import logging
import sys
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.routes import routers as v1_routers
from app.core.config import configs
from app.core.container import Container
from app.util.class_object import singleton

from starlette.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("/tmp/app.log")],
)
logger = logging.getLogger(__name__)


class HealthCheckFilter(logging.Filter):
    """Suppress uvicorn access logs for the /health endpoint."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


# Suppress noisy health-check logs from uvicorn access logger
logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())


@singleton
class AppCreator:
    def __init__(self):
        logger.info("Initializing FastAPI application...")

        # set app default
        self.app = FastAPI(
            title=configs.PROJECT_NAME,
            openapi_url=f"{configs.API}/openapi.json",
            version="0.0.1",
        )

        # set db and container
        logger.info("Setting up database and dependency injection container...")
        self.container = Container()
        self.container.wire(modules=[__name__])
        self.db = self.container.db()
        logger.info("Database and container initialized successfully")

        # auto-create tables
        try:
            SQLModel.metadata.create_all(self.db.engine)
            logger.info("Database tables ensured via SQLModel.metadata.create_all")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")

        # set CORS middleware
        logger.info("Configuring CORS middleware...")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=configs.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("CORS middleware configured successfully")

        # set routes
        @self.app.get("/")
        def root():
            return "service is working"

        @self.app.get("/health", include_in_schema=False)
        def health():
            return JSONResponse(content={"status": "ok"})

        self.app.include_router(v1_routers, prefix=configs.API_V1_STR)
        logger.info(f"Routes registered. API available at {configs.API_V1_STR}")


app_creator = AppCreator()
app = app_creator.app
db = app_creator.db
container = app_creator.container
