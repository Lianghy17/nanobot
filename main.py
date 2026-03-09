"""Nanobot FastAPI Application Entry Point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nanobot.api.routes import router
from nanobot.config.settings import get_settings
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.rag_tool import RAGTool
from nanobot.agent.tools.sql_tool import SQLTool
from nanobot.agent.tools.time_series_tool import TimeSeriesForecastTool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    settings = get_settings()

    # Startup: Initialize tools
    registry = ToolRegistry()
    if settings.rag_enabled:
        registry.register(RAGTool())
    if settings.sql_enabled:
        registry.register(SQLTool())
    if settings.ts_enabled:
        registry.register(TimeSeriesForecastTool())

    app.state.tool_registry = registry
    print(f"🚀 Nanobot started with {len(registry.list_tools())} tools")

    yield

    # Shutdown
    print("🛑 Nanobot shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Nanobot API",
        description="Multi-user AI Agent Service with RAG, SQL, and Time Series tools",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(router, prefix="/api/v1")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "nanobot"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
