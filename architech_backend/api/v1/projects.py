from fastapi import APIRouter, Depends, HTTPException, Request
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
from core.security import get_api_key
from core.rate_limit import limiter

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
@limiter.limit("5/minute")
def create_project(
    project_in: schemas.ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
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

class TriggerResponse(schemas.BaseModel):
    job_id: UUID

@router.post("/trigger", response_model=TriggerResponse, status_code=202)
@limiter.limit("5/minute")
def trigger_project(
    project_in: schemas.ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Zapier input trigger: accepts an idea + webhook URL, runs the pipeline async, returns a job ID.
    """
    new_project = Project(
        initial_idea=project_in.initial_idea,
        zapier_webhook_url=project_in.zapier_webhook_url
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    generation_chain = chain(
        task_generate_blueprint.s(str(new_project.id)),
        task_run_simulation.s()
    )
    
    generation_chain.apply_async()

    return TriggerResponse(job_id=new_project.id)

@router.get("/jobs/{job_id}", response_model=schemas.ProjectStatusResponse)
def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Zapier polling endpoint to check the status of a triggered job.
    """
    # Reuse the existing status logic
    return get_project_status(job_id, db)

@router.get("/{project_id}/n8n-workflow")
def export_n8n_workflow(
    project_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Generates a valid n8n workflow JSON that recreates the automation.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    base_url = str(request.base_url).rstrip('/')
    trigger_url = f"{base_url}/api/v1/trigger"

    workflow_json = {
        "name": f"ArchiTECH Auto-Plan: {project.initial_idea[:30]}...",
        "nodes": [
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "architech-trigger",
                    "options": {}
                },
                "name": "Webhook Trigger",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [250, 300]
            },
            {
                "parameters": {
                    "authentication": "headerAuth",
                    "method": "POST",
                    "url": trigger_url,
                    "sendBody": True,
                    "bodyParameters": {
                        "parameters": [
                            {"name": "initial_idea", "value": "={{$json.body.idea}}"},
                            {"name": "zapier_webhook_url", "value": "={{$execution.resumeUrl}}"}
                        ]
                    },
                    "options": {}
                },
                "name": "Call ArchiTECH",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 3,
                "position": [450, 300],
                "credentials": {
                    "httpHeaderAuth": {
                        "id": "YOUR_ARCHITECH_CREDENTIAL_ID",
                        "name": "Header Auth account"
                    }
                }
            },
            {
                "parameters": {
                    "channel": "general",
                    "text": "=New Product Plan Ready!\nThemes: {{$json.body.themes}}\nTrello Board: {{$json.body.trello_board_url}}",
                    "otherOptions": {}
                },
                "name": "Slack Notification",
                "type": "n8n-nodes-base.slack",
                "typeVersion": 2,
                "position": [650, 100]
            },
            {
                "parameters": {
                    "operation": "create",
                    "databaseId": "YOUR_NOTION_DB_ID",
                    "propertiesUi": {
                        "propertyValues": [
                            {"key": "Name|title", "value": "={{$json.body.idea}}"},
                            {"key": "Trello|url", "value": "={{$json.body.trello_board_url}}"}
                        ]
                    }
                },
                "name": "Save to Notion",
                "type": "n8n-nodes-base.notion",
                "typeVersion": 2,
                "position": [650, 300]
            },
            {
                "parameters": {
                    "operation": "create",
                    "listId": "YOUR_TRELLO_LIST_ID",
                    "name": "={{$json.body.idea}}",
                    "description": "=Trello Board: {{$json.body.trello_board_url}}"
                },
                "name": "Save to Trello",
                "type": "n8n-nodes-base.trello",
                "typeVersion": 1,
                "position": [650, 500]
            }
        ],
        "connections": {
            "Webhook Trigger": {
                "main": [
                    [{"node": "Call ArchiTECH", "type": "main", "index": 0}]
                ]
            },
            "Call ArchiTECH": {
                "main": [
                    [
                        {"node": "Slack Notification", "type": "main", "index": 0}, 
                        {"node": "Save to Notion", "type": "main", "index": 0},
                        {"node": "Save to Trello", "type": "main", "index": 0}
                    ]
                ]
            }
        },
        "settings": {},
        "meta": {"templateId": "architech-export-1"}
    }
    
    return workflow_json