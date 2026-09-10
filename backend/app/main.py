"""
CloudIntelliGuard — FastAPI Application Entry Point

All routes are prefixed with /api/v1/.
Startup: creates DB tables, seeds default roles and admin user.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.database.connection import init_db
from app.database.seed import seed_defaults

# API routers
from app.api import (
    alerts, anomalies, attack_path, audit, auth, copilot, datasets,
    enforcements, evaluation, events, graph, incidents, reports, risk,
    simulator, uba, users,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise DB on startup."""
    logger.info(f"Starting {settings.app_name} (debug={settings.debug}, demo={settings.demo_mode})")
    await init_db()
    from app.database.connection import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await seed_defaults(db)
    logger.info("Database ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.app_name,
    description=(
        "Explainable and Adaptive AI Framework for Proactive Cloud Security "
        "and User Behavior Intelligence. Enterprise SOC Edition."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — restrict in production via environment variables
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route registration ────────────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(auth.router,         prefix=f"{API_PREFIX}/auth",           tags=["Authentication"])
app.include_router(users.router,        prefix=f"{API_PREFIX}/users",          tags=["System Users"])
app.include_router(datasets.router,     prefix=f"{API_PREFIX}/datasets",       tags=["Datasets"])
app.include_router(events.router,       prefix=f"{API_PREFIX}/events",         tags=["Cloud Events"])
app.include_router(graph.router,        prefix=f"{API_PREFIX}/graph",          tags=["Graph Windows"])
app.include_router(anomalies.router,    prefix=f"{API_PREFIX}/detection",      tags=["Anomaly Detection"])
app.include_router(risk.router,         prefix=f"{API_PREFIX}/risk",           tags=["Risk Scores"])
app.include_router(incidents.router,    prefix=f"{API_PREFIX}/incidents",      tags=["Incidents"])
app.include_router(alerts.router,       prefix=f"{API_PREFIX}/alerts",         tags=["Alerts"])
app.include_router(reports.router,      prefix=f"{API_PREFIX}/reports",        tags=["Reports"])
app.include_router(evaluation.router,   prefix=f"{API_PREFIX}/evaluation",     tags=["Evaluation"])
app.include_router(enforcements.router, prefix=f"{API_PREFIX}/response",       tags=["Automated Response"])
app.include_router(uba.router,          prefix=f"{API_PREFIX}/uba",            tags=["User Behavior Analytics"])
app.include_router(attack_path.router,  prefix=f"{API_PREFIX}/attack-path",    tags=["Attack Path Analysis"])
app.include_router(simulator.router,    prefix=f"{API_PREFIX}/risk-simulator", tags=["What-If Risk Simulator"])
app.include_router(copilot.router,      prefix=f"{API_PREFIX}/copilot",        tags=["AI Copilot"])
app.include_router(audit.router,        prefix=f"{API_PREFIX}/audit",          tags=["Audit Logs"])



@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "demo_mode": settings.demo_mode,
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
