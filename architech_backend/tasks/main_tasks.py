import time
import uuid
import json 
from celery import shared_task, chain
from db.session import SessionLocal
from db.models import Project, ProjectStatus
from core.config import settings

# --- 1. IMPORT THE BOTS & NEW PYDANTIC MODELS ---
from .ai_crews import run_blueprint_crew, run_adversarial_crew, BlueprintOutput
from .trello_bot import create_trello_board


@shared_task(bind=True)
def task_generate_blueprint(self, project_id: str):
    """
    Task 1: Runs the Blueprint Crew to generate the initial plan.
    """
    db = SessionLocal()
    project = None 
    try:
        project_id_uuid = uuid.UUID(project_id)
        project = db.query(Project).filter(Project.id == project_id_uuid).first()
        if not project:
            raise Exception("Project not found")

        project.status = ProjectStatus.BLUEPRINTING
        db.commit()

        # --- UPDATED: We now receive a Pydantic object ---
        result_object: BlueprintOutput = run_blueprint_crew(project.initial_idea)
        
        # Convert the Pydantic object to a JSON string for database storage
        project.initial_plan_json = result_object.model_dump_json(indent=2)
        db.commit()
        # --- END OF UPDATE ---
        
        # Pass project_id and project_name to the next task
        return project_id, project.initial_idea 
    
    except Exception as e:
        if project: 
            project.status = ProjectStatus.FAILED
            project.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()

@shared_task(bind=True)
def task_run_simulation(self, results_from_task_1: tuple):
    """
    Task 2: Runs the Adversarial Crew and creates the Trello Board.
    """
    project_id, project_name = results_from_task_1
    db = SessionLocal()
    project = None 
    try:
        project_id_uuid = uuid.UUID(project_id)
        project = db.query(Project).filter(Project.id == project_id_uuid).first()
        if not project:
            raise Exception("Project not found")

        project.status = ProjectStatus.SIMULATING
        db.commit()
        
        # --- UPDATED: We must now parse the DB JSON back into a Pydantic object ---
        # 1. Read the JSON string from the database
        initial_plan_str = project.initial_plan_json
        
        # 2. Parse the string into the Pydantic model
        initial_plan_obj: BlueprintOutput = BlueprintOutput.model_validate_json(initial_plan_str)
        
        # 3. Pass the Pydantic object to the adversarial crew
        # stressed_plan_models is now a LIST of Pydantic 'AdversarialUserStory' objects
        # report_dict is now a clean DICTIONARY
        stressed_plan_models, report_dict = run_adversarial_crew(initial_plan_obj)

        # 4. Convert the Pydantic models to a simple list of dictionaries
        stressed_plan_list_of_dicts = [story.model_dump() for story in stressed_plan_models]
        
        # 5. Save this list of dicts as a JSON string in the database
        project.stressed_plan_json = json.dumps(stressed_plan_list_of_dicts, indent=2)
        
        # Convert the report dict to a clean string
        report_str = json.dumps(report_dict, indent=2) 
        project.premortem_report = report_str
        # --- END OF UPDATE ---
        
        # --- 4. CALL THE REAL TRELLO BOT ---
        if settings.TRELLO_API_KEY == "YOUR_TRELLO_API_KEY":
            print("--- TRELLO BOT: SKIPPING - API KEY IS A PLACEHOLDER ---")
            trello_url = "https://trello.com/b/skipped-placeholder"
        else:
            # --- UPDATED: Pass the clean list of dicts to the bot ---
            trello_url = create_trello_board(
                settings.TRELLO_API_KEY,
                settings.TRELLO_API_TOKEN,
                project_name, 
                stressed_plan_list_of_dicts,  # <-- Pass the clean list of dicts
                report_str
            )
        # --- End Bot Logic ---
        
        project.trello_board_url = trello_url
        project.status = ProjectStatus.COMPLETE
        db.commit()

        return project_id

    except Exception as e:
        if project: 
            project.status = ProjectStatus.FAILED
            project.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()

