"""FastAPI control plane for the Rorven workbench."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rorven.composition import create_local_services
from rorven_api.routes import register_routes
from rorven_api.worker_supervisor import create_worker_supervisor


def create_app() -> FastAPI:
    services = create_local_services()
    worker_supervisor = create_worker_supervisor(services.worker)
    print(f"[rorven-api] initialized with {len(services.projects.list_projects())} projects", flush=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.worker_supervisor = worker_supervisor
        worker_supervisor.start()
        print(f"[rorven-api] embedded worker: {worker_supervisor.status_dict()}", flush=True)
        try:
            yield
        finally:
            worker_supervisor.stop()

    app = FastAPI(title="Rorven API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in development
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_routes(app, services, worker_supervisor.status_dict)
    return app


app = create_app()
