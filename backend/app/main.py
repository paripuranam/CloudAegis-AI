"""CloudAegis AI Main FastAPI Application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.core.config import settings
from app.api import routes
from app.db.database import engine
from app.db.base import Base
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def ensure_cloud_account_schema() -> None:
    """Backfill additive schema changes for existing deployments."""
    statements = [
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'findingtypeenum') THEN
                CREATE TYPE findingtypeenum AS ENUM ('SECURITY', 'COST', 'COMPLIANCE');
            END IF;
        END
        $$;
        """,
        "ALTER TABLE cloud_accounts ADD COLUMN IF NOT EXISTS auth_method VARCHAR NOT NULL DEFAULT 'role_arn'",
        "ALTER TABLE cloud_accounts ADD COLUMN IF NOT EXISTS access_key_id VARCHAR NULL",
        "ALTER TABLE cloud_accounts ADD COLUMN IF NOT EXISTS secret_access_key VARCHAR NULL",
        "ALTER TABLE cloud_accounts ALTER COLUMN role_arn DROP NOT NULL",
        "ALTER TABLE findings ADD COLUMN IF NOT EXISTS finding_type findingtypeenum NULL DEFAULT 'SECURITY'",
        "ALTER TABLE findings ADD COLUMN IF NOT EXISTS benchmark_metadata JSON NULL",
        "ALTER TABLE remediation_plans ADD COLUMN IF NOT EXISTS security_remediation TEXT NULL",
        "ALTER TABLE remediation_plans ADD COLUMN IF NOT EXISTS cost_optimization TEXT NULL",
    ]

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:
                logger.warning(f"Schema update skipped for statement '{statement}': {exc}")


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("CloudAegis AI API starting up...")
    Base.metadata.create_all(bind=engine)
    ensure_cloud_account_schema()
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logger.info("CloudAegis AI API shutting down...")


# Create FastAPI app
app = FastAPI(
    title="CloudAegis AI API",
    description="Unified cloud governance platform for security, cost, and decision intelligence",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(routes.router, prefix="/api/v1", tags=["security"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "CloudAegis AI",
        "version": "1.0.0",
        "description": "Unified cloud governance platform",
        "api_docs": "/docs",
    }


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}")
    return {
        "error": "Internal server error",
        "detail": str(exc) if settings.api_env == "development" else "An error occurred",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_env == "development"
    )
