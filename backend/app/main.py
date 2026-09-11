import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.core.logging import logger
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing application resources and database...")
    init_db()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Intelligent Document Extraction, Validation & REST API Platform for Financial Services",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API Routers
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)

# Frontend Static and Templates mounting
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_dir = os.path.join(base_dir, "frontend")
static_dir = os.path.join(frontend_dir, "static")
templates_dir = os.path.join(frontend_dir, "templates")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

sample_docs_dir = os.path.join(base_dir, "data", "sample_documents")
if os.path.exists(sample_docs_dir):
    app.mount("/data/sample_documents", StaticFiles(directory=sample_docs_dir), name="sample_documents")

templates = Jinja2Templates(directory=templates_dir) if os.path.exists(templates_dir) else None


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard(request: Request):
    """Serves the interactive web dashboard."""
    if templates:
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"project_name": settings.PROJECT_NAME},
        )
    return HTMLResponse("<h1>Financial Document Intelligence Dashboard</h1>")


@app.get("/documents/{document_name}/view", response_class=HTMLResponse, include_in_schema=False)
async def serve_document_view(request: Request, document_name: str):
    """Serves the detailed extraction & validation view for a document."""
    if templates:
        return templates.TemplateResponse(
            request=request,
            name="document_result.html",
            context={"document_name": document_name, "project_name": settings.PROJECT_NAME},
        )
    return HTMLResponse(f"<h1>Document Detail: {document_name}</h1>")


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error processing {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the request.",
            }
        },
    )
