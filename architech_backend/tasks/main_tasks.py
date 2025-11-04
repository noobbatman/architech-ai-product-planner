import time
import uuid
import json 
from celery import shared_task, chain
from db.session import SessionLocal
from db.models import Project, ProjectStatus
from core.config import settings

# --- 1. IMPORT THE BOTS ---
from .ai_crews import run_blueprint_crew, run_adversarial_crew
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

        result_json = run_blueprint_crew(project.initial_idea)
        project.initial_plan_json = result_json
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
        
        initial_plan = project.initial_plan_json
        stressed_plan, report_dict = run_adversarial_crew(initial_plan) # Renamed 'report' to 'report_dict'

        project.stressed_plan_json = stressed_plan
        # Convert the report dict to a clean string
        report_str = json.dumps(report_dict, indent=2) 
        project.premortem_report = report_str
        
        # --- 4. CALL THE REAL TRELLO BOT ---
        # Get your new, safe keys from the .env file.
        
        # === FIX 1: The 'if' check MUST look for a placeholder in the settings ===
        if settings.TRELLO_API_KEY == "YOUR_TRELLO_API_KEY":
            print("--- TRELLO BOT: SKIPPING - API KEY IS A PLACEHOLDER ---")
            trello_url = "https://trello.com/b/skipped-placeholder"
        else:
            # === FIX 2: Pass all 5 arguments to the bot ===
            trello_url = create_trello_board(
                settings.TRELLO_API_KEY,
                settings.TRELLO_API_TOKEN,
                project_name,    # Use the idea name for the board
                stressed_plan,   # Pass the final AI plan
                report_str       # Pass the report for the board description
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