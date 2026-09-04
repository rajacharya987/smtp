"""FastAPI application entrypoint."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from mailgate import __version__
from mailgate.api import auth, dns_api, domains, forwarders, logs, queue, settings, setup, system
from mailgate.config import load_config
from mailgate.db import init_db
from mailgate.paths import WEB_DIR
from mailgate.ratelimit import enforce
from mailgate.security import ensure_jwt_secret


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path.startswith("/api/"):
            response.headers["X-Robots-Tag"] = "noindex"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/"):
            cfg = load_config()
            try:
                enforce(
                    request,
                    name="api",
                    limit=cfg.security.rate_limit_per_minute,
                    window_seconds=60,
                )
            except Exception as exc:
                from fastapi import HTTPException

                if isinstance(exc, HTTPException):
                    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
                raise
        return await call_next(request)


def create_app() -> FastAPI:
    cfg = load_config()
    app = FastAPI(
        title="MailGate",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    origins = list(cfg.web.cors_origins)
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

    app.include_router(auth.router)
    app.include_router(setup.router)
    app.include_router(domains.router)
    app.include_router(forwarders.router)
    app.include_router(logs.router)
    app.include_router(queue.router)
    app.include_router(dns_api.router)
    app.include_router(settings.router)
    app.include_router(system.router)

    @app.on_event("startup")
    def _startup() -> None:
        ensure_jwt_secret()
        init_db()

    @app.get("/api/version")
    def version():
        return {"name": "MailGate", "version": __version__}

    web = Path(WEB_DIR)
    if web.exists():
        app.mount("/", StaticFiles(directory=str(web), html=True), name="web")

    return app


app = create_app()
