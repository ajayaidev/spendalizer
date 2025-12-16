"""
SpendAlizer API - Personal Finance Management Application
A modular FastAPI backend for managing personal finances.
"""
import os
import logging
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

# Import database and services
from database import db, close_db
from services.categorization import init_default_categories

# Import all route modules
from routes.auth import router as auth_router
from routes.accounts import router as accounts_router
from routes.categories import router as categories_router
from routes.transactions import router as transactions_router
from routes.rules import router as rules_router
from routes.analytics import router as analytics_router
from routes.settings import router as settings_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the main FastAPI app
app = FastAPI(
    title="SpendAlizer API",
    description="Personal Finance Management Application",
    version="2.0.0"
)

# Create API router with /api prefix
api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(auth_router)
api_router.include_router(accounts_router)
api_router.include_router(categories_router)
api_router.include_router(transactions_router)
api_router.include_router(rules_router)
api_router.include_router(analytics_router)
api_router.include_router(settings_router)

# Include the API router in the main app
app.include_router(api_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize default categories and log startup."""
    await init_default_categories()
    logger.info("SpendAlizer API started (v2.0.0 - Modular Architecture)")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    await close_db()
    logger.info("SpendAlizer API shutdown complete")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}
