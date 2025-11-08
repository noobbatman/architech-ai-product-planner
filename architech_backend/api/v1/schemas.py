from pydantic import BaseModel, Field
from uuid import UUID
from db.models import ProjectStatus
from typing import Optional, List, Dict, Any # Added Dict, Any
import datetime

# --- Input ---
class ProjectCreate(BaseModel):
    initial_idea: str = Field(default=..., min_length=10, example="An app to find local dog walkers")

# --- Output Schemas ---

class ProjectStatusResponse(BaseModel):
    project_id: UUID = Field(alias='id')
    status: ProjectStatus
    message: str
    trello_board_url: Optional[str] = None
    frontend_summary: Optional[str] = None
    
    # --- ADDED FOR ROBUSTNESS (Internal fields needed for validation) ---
    initial_plan_json: Optional[Dict[str, Any]] = None
    stressed_plan_json: Optional[List[Dict[str, Any]]] = None # Changed to List[Dict[str, Any]]
    premortem_report: Optional[str] = None
    # ------------------------------------------------------------------

    class Config:
        from_attributes = True
        populate_by_name = True

class ProjectListItem(BaseModel):
    project_id: UUID = Field(alias='id')
    initial_idea: str
    status: ProjectStatus
    trello_board_url: Optional[str] = None
    created_at: datetime.datetime
    frontend_summary: Optional[str] = None
    
    # --- ADDED FOR ROBUSTNESS (Internal fields needed for validation) ---
    initial_plan_json: Optional[Dict[str, Any]] = None
    stressed_plan_json: Optional[List[Dict[str, Any]]] = None # Changed to List[Dict[str, Any]]
    premortem_report: Optional[str] = None
    # ------------------------------------------------------------------

    class Config:
        from_attributes = True
        populate_by_name = True