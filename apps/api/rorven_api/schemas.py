from __future__ import annotations

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1)
    allowed_root: str = Field(min_length=1)
    workspace_root: str = Field(min_length=1)


class SubmitRunRequest(BaseModel):
    command: str = Field(min_length=1)


class WorkOnceRequest(BaseModel):
    worker_id: str = Field(default="local-worker", min_length=1)
    limit: int = Field(default=2, ge=1, le=10)
