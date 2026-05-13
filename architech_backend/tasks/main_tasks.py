import uuid
import json 
from celery import shared_task
from db.session import SessionLocal
from db.models import Project, ProjectStatus
from core.config import settings

# --- 1. CLEAN IMPORTS ---
# Import the new Summary Agent and the helper functions/classes from ai_crews
from .ai_crews import run_blueprint_crew, run_adversarial_crew, run_summary_agent, BlueprintOutput
from .trello_bot import create_trello_board
from core.logger import setup_logger

logger = setup_logger(__name__)


@shared_task(bind=True)
def task_generate_blueprint(self, project_id: str):
    """
    Task 1: Runs the Blueprint Crew and saves the Pydantic model output as JSON.
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

        # Run the AI crew (returns Pydantic BlueprintOutput object)
        result_object: BlueprintOutput = run_blueprint_crew(project.initial_idea)
        
        # Save the Pydantic object as a JSON string to the database (JSONB column)
        project.initial_plan_json = result_object.model_dump_json(indent=2)
        db.commit()
        
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
    Task 2: Runs Adversarial Crew, Summary Agent, and creates the Trello Board.
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
        
        # 1. Prepare initial plan object from DB JSON string
        initial_plan_str = project.initial_plan_json
        initial_plan_obj = BlueprintOutput.model_validate_json(initial_plan_str)
        
        # 2. Run Adversarial Crew (returns list of Pydantic models and a dict report)
        stressed_plan_models, report_dict = run_adversarial_crew(initial_plan_obj)

        # 3. Prepare data for storage/summary
        # Convert the list of Pydantic models back to a standard list of dicts for DB/Trello
        stressed_plan_list_of_dicts = [story.model_dump() for story in stressed_plan_models]
        
        # Convert the report dict to a clean string for the Summary Agent/DB TEXT column
        report_str = json.dumps(report_dict, indent=2)

        # 4. Run the NEW Summary Agent
        summary_text = run_summary_agent(stressed_plan_list_of_dicts, report_dict)
        
        # 5. Save final outputs to the database
        project.stressed_plan_json = json.dumps(stressed_plan_list_of_dicts, indent=2) # Save as clean JSON string
        project.premortem_report = report_str
        project.frontend_summary = summary_text  # <-- Save the simple summary

        # 6. Call the Real Trello Bot
        # NOTE: Using settings, which is correct for a robust app
        TRELLO_API_KEY = settings.TRELLO_API_KEY 
        TRELLO_API_TOKEN = settings.TRELLO_API_TOKEN 

        if TRELLO_API_KEY == "YOUR_TRELLO_API_KEY_HERE" or TRELLO_API_KEY == "YOUR_TRELLO_API_KEY" or not TRELLO_API_KEY:
            logger.info("TRELLO BOT: SKIPPING - API KEY IS A PLACEHOLDER")
            trello_url = "https://trello.com/b/skipped-placeholder"
        else:
            trello_url = create_trello_board(
                TRELLO_API_KEY,
                TRELLO_API_TOKEN,
                project_name, 
                stressed_plan_list_of_dicts, 
                report_str
            )
        
        project.trello_board_url = trello_url
        project.status = ProjectStatus.COMPLETE
        db.commit()

        # 7. Call Zapier Webhook if provided
        if project.zapier_webhook_url:
            import requests
            try:
                # Need to parse initial_plan to get themes
                themes = initial_plan_obj.themes if hasattr(initial_plan_obj, 'themes') else []
                
                payload = {
                    "project_id": str(project.id),
                    "idea": project.initial_idea,
                    "themes": themes,
                    "user_stories": stressed_plan_list_of_dicts,
                    "trello_board_url": trello_url
                }
                response = requests.post(project.zapier_webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"ZAPIER WEBHOOK CALLED SUCCESSFULLY: {project.zapier_webhook_url}")
            except requests.exceptions.RequestException as zap_e:
                logger.error(f"ZAPIER WEBHOOK FAILED: {str(zap_e)}. Retrying in 60s...")
                # Retry webhook delivery
                raise self.retry(exc=zap_e, countdown=60, max_retries=3)

        return project_id

    except Exception as e:
        if project: 
            project.status = ProjectStatus.FAILED
            project.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()