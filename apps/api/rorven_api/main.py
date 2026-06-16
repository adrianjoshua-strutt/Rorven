"""FastAPI control plane for the durable walking skeleton."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rorven.composition import create_local_services
from rorven_api.routes import register_routes


def create_app() -> FastAPI:
    services = create_local_services()
    print(f"[rorven-api] initialized with {len(services.projects.list_projects())} projects", flush=True)
    app = FastAPI(title="Rorven API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_routes(app, services)
    return app


app = create_app()
