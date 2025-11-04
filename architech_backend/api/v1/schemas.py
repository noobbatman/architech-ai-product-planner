from pydantic import BaseModel, Field
from uuid import UUID
from db.models import ProjectStatus
from typing import Optional

# --- Input ---
class ProjectCreate(BaseModel):
    initial_idea: str = Field(default=..., min_length=10, example="An app to find local dog walkers")

# --- Output ---
class ProjectStatusResponse(BaseModel):
    project_id: UUID
    status: ProjectStatus
    message: str
    trello_board_url: Optional[str] = None

    class Config:
        from_attributes = True