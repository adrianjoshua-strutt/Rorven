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


class RootMessageRequest(BaseModel):
    message: str = Field(min_length=1)


class ModelProfileSettingsRequest(BaseModel):
    utility: str | None = None
    balanced: str | None = None
    reasoning: str | None = None
    frontier: str | None = None


class ProjectDefaultsSettingsRequest(BaseModel):
    workspace_base_root: str = Field(min_length=1)


class ApprovalPolicySettingsRequest(BaseModel):
    text_file_write: str = Field(min_length=1)
