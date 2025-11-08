from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from celery import chain
from uuid import UUID
from typing import List
import json # <--- ADD THIS IMPORT

from db.session import get_db
from db.models import Project, ProjectStatus
from api.v1 import schemas
from tasks.main_tasks import task_generate_blueprint, task_run_simulation

router = APIRouter()

@router.get("", response_model=List[schemas.ProjectListItem])
def get_all_projects(db: Session = Depends(get_db)):
    """
    Get a list of all projects, ordered by creation date.
    This function contains defensive logic to handle old/corrupted JSON formats.
    """
    projects = db.query(Project).order_by(desc(Project.created_at)).all()
    
    result = []
    for p in projects:
        project_dict = p.__dict__.copy()
        
        # 1. Load JSON strings into Python dictionaries for the robust fields
        if project_dict.get('initial_plan_json') is not None and isinstance(project_dict['initial_plan_json'], str):
             project_dict['initial_plan_json'] = json.loads(project_dict['initial_plan_json'])
        
        # 2. Handle the problematic stressed_plan_json field
        if project_dict.get('stressed_plan_json') is not None:
            raw_stressed_json = project_dict['stressed_plan_json']
            
            # Ensure it's a dictionary object before trying to extract keys
            if isinstance(raw_stressed_json, str):
                 try:
                     raw_stressed_json = json.loads(raw_stressed_json)
                 except json.JSONDecodeError:
                     raw_stressed_json = {} # Set to empty dict on decode error

            # **THE FIX**: Check for the old dictionary-based structures and extract the list.
            if isinstance(raw_stressed_json, dict):
                # Check for the old model key that contained the list of stories
                if 'user_stories' in raw_stressed_json:
                    project_dict['stressed_plan_json'] = raw_stressed_json['user_stories']
                elif 'stressed_plan' in raw_stressed_json:
                    # Check for the dictionary that contained the final plan
                    if isinstance(raw_stressed_json['stressed_plan'], list):
                        project_dict['stressed_plan_json'] = raw_stressed_json['stressed_plan']
                    else:
                        project_dict['stressed_plan_json'] = []
                else:
                    # Default to empty list if it's a dict but doesn't have the expected list key
                    project_dict['stressed_plan_json'] = []
            elif isinstance(raw_stressed_json, list):
                 # The data is already a clean list (the expected format)
                 project_dict['stressed_plan_json'] = raw_stressed_json
            else:
                 # Default to empty list if format is unhandled
                 project_dict['stressed_plan_json'] = []

        # 3. Now validate the clean Python dictionary
        result.append(schemas.ProjectListItem.model_validate(project_dict))
        
    return result


@router.post("/generate", response_model=schemas.ProjectStatusResponse, status_code=202)
def create_project(
    project_in: schemas.ProjectCreate,
    db: Session = Depends(get_db)
):
    new_project = Project(
        initial_idea=project_in.initial_idea
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    generation_chain = chain(
        task_generate_blueprint.s(str(new_project.id)),
        task_run_simulation.s()
    )
    
    generation_chain.apply_async()

    return schemas.ProjectStatusResponse(
        project_id=new_project.id,
        status=new_project.status,
        message="Project accepted. Generation is in progress.",
        trello_board_url=None
    )


@router.get("/{project_id}/status", response_model=schemas.ProjectStatusResponse)
def get_project_status(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    message = ""
    if project.status == ProjectStatus.PENDING:
        message = "Your project is queued for generation."
    elif project.status == ProjectStatus.BLUEPRINTING:
        message = "The AI crew is generating the blueprint..."
    elif project.status == ProjectStatus.SIMULATING:
        message = "The Adversarial Crew is stress-testing your plan."
    elif project.status == ProjectStatus.COMPLETE:
        message = "Generation complete! Your board is ready."
    elif project.status == ProjectStatus.FAILED:
        message = f"Generation failed: {project.error_message}"

    return schemas.ProjectStatusResponse(
        project_id=project.id,
        status=project.status,
        message=message,
        trello_board_url=project.trello_board_url
    )