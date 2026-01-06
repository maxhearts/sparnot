"""FastAPI backend for Pre-Production Compiler UI."""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Import routers
from .routers import projects, schemas, compile, diff, scenes, locks, assistant

# Get data directory (default to parent's data/)
DATA_DIR = Path(__file__).parent.parent.parent / "data"

app = FastAPI(
    title="Narrative Orchestrator API",
    description="API for Pre-Production Compiler UI",
    version="0.1.0"
)

# CORS middleware - allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(schemas.router, prefix="/api/projects", tags=["schemas"])
app.include_router(compile.router, prefix="/api/projects", tags=["compile"])
app.include_router(diff.router, prefix="/api/projects", tags=["diff"])
app.include_router(scenes.router, prefix="/api/projects", tags=["scenes"])
app.include_router(locks.router, prefix="/api/projects", tags=["locks"])
app.include_router(assistant.router, prefix="/api/projects", tags=["assistant"])

# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "data_dir": str(DATA_DIR)}


# Serve React app in production (after build)
# In development, React dev server handles this
if os.getenv("ENV") == "production":
    build_dir = Path(__file__).parent.parent / "web" / "dist"
    if build_dir.exists():
        app.mount("/static", StaticFiles(directory=str(build_dir / "static")), name="static")
        
        @app.get("/{full_path:path}")
        async def serve_react_app(full_path: str):
            """Serve React app for all non-API routes."""
            if full_path.startswith("api/"):
                return {"error": "Not found"}
            file_path = build_dir / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            # Default to index.html for SPA routing
            return FileResponse(build_dir / "index.html")

