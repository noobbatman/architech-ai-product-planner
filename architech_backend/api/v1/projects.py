from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from celery import chain
from uuid import UUID

from db.session import get_db
from db.models import Project, ProjectStatus # <-- FIX 4: Imported ProjectStatus
from api.v1 import schemas
from tasks.main_tasks import task_generate_blueprint, task_run_simulation

router = APIRouter()

@router.post("/generate", response_model=schemas.ProjectStatusResponse, status_code=202)
def create_project(
    project_in: schemas.ProjectCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new project and kick off the asynchronous generation pipeline.
    """
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
        message="Project accepted. Generation is in progress."
    )


@router.get("/{project_id}/status", response_model=schemas.ProjectStatusResponse)
def get_project_status(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Poll this endpoint to get the status of a project.
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    message = ""
    # v-- This area now works thanks to the import
    if project.status == ProjectStatus.PENDING:
        message = "Your project is queued for generation."
    elif project.status == ProjectStatus.BLUEPRINTING:
        message = "The AI crew is generating the blueprint..."
    elif project.status == ProjectStatus.SIMULATING:
        message = "The Adversarial Crew is stress-testing your plan..."
    elif project.status == ProjectStatus.COMPLETE:
        message = "Generation complete! Your board is ready."
    elif project.status == ProjectStatus.FAILED:
        message = f"Generation failed: {project.error_message}"
    # ^-- This area now works thanks to the import

    # This is a cleaner way to create the response
    response_data = schemas.ProjectStatusResponse(
        project_id=project.id,
        status=project.status,
        message=message,
        trello_board_url=project.trello_board_url
    )
    return response_data