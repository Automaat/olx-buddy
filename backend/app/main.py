"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import generate, listings
from app.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan events."""
    # Startup
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown()


app = FastAPI(
    title="OLX Buddy",
    description="Vinted/OLX sales management app",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local vite
        "http://frontend:5173",  # Docker vite
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(listings.router)
app.include_router(generate.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "OLX Buddy API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
