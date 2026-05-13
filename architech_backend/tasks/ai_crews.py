import os
import json
from typing import Tuple, List, Dict, Any
from crewai import Agent, Task, Crew, Process
from core.config import settings
from pydantic import BaseModel, Field

# --- LLM CONFIGURATION ---
os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("GOOGLE_API_KEY", None)
main_llm = "anthropic/claude-3-5-sonnet-20241022"

# --- ============================ ---
# --- PYDANTIC "DATA CONTRACTS" ---
# --- ============================ ---

# --- 1. Blueprint Crew Models ---

class BlueprintUserStory(BaseModel):
    """Defines the structure for a single user story from the blueprint crew."""
    id: str = Field(description="A unique ID for the user story, e.g., 'US001'.")
    name: str = Field(description="The concise title of the user story.")
    description: str = Field(description="The full user story text in 'As a user...' format.")

class BlueprintOutput(BaseModel):
    """Defines the final JSON output structure for the blueprint crew."""
    themes: List[str] = Field(description="A list of 3-5 strategic product themes.")
    user_stories: List[BlueprintUserStory] = Field(description="The initial list of user stories based on the themes.")

# --- 2. Adversarial Crew Models ---

class AdversarialUserStory(BaseModel):
    """
    Defines the structure for a single *stress-tested* user story.
    """
    id: str = Field(description="The original user story ID, e.g., 'US001'.")
    name: str = Field(description="The original title/name of the user story.")
    original_description: str = Field(description="The original user story description.")
    risk_considerations: str = Field(description="A detailed paragraph summarizing all identified risks and mitigation strategies for *this* story.")
    impacted_market_shocks: List[str] = Field(description="List of Market Shock IDs that impact this story.")
    impacted_technical_risks: List[str] = Field(description="List of Technical Risk IDs that impact this story.")

class AdversarialOutput(BaseModel):
    """Defines the final JSON output structure for the adversarial crew."""
    stressed_plan: List[AdversarialUserStory] = Field(description="The complete, final, battle-hardened list of user stories, formatted as AdversarialUserStory objects.")
    premortem_report: Dict[str, Any] = Field(description="A dictionary-based report of the full adversarial analysis, its findings, and key risks.")


def _clean_json_output(raw_output: str) -> str:
    """
    Helper function to clean the raw JSON output from a CrewAI task.
    It removes markdown code fences and extracts the JSON object or array.
    """
    # Check if the output contains the JSON markdown fences
    if "```json" in raw_output:
        # Strip the fences and any leading/trailing whitespace
        start_index = raw_output.find("```json") + 7
        end_index = raw_output.rfind("```")
        if end_index > start_index:
            json_part = raw_output[start_index:end_index].strip()
            try:
                # Validate and re-format the JSON to fix minor syntax errors
                loaded_json = json.loads(json_part)
                return json.dumps(loaded_json)
            except json.JSONDecodeError:
                # If it's not valid JSON, return the cleaned part and let pydantic handle it
                return json_part
    
    # If the fences are not present, return the original string
    return raw_output


# --- ============================ ---
# --- 1. BLUEPRINT CREW (TASK 1) ---
# --- ============================ ---
def run_blueprint_crew(product_idea: str) -> BlueprintOutput:
    """
    Runs the initial "Blueprint Crew" to turn a product idea into a developer-ready plan.
    """
    # (Agent definitions are unchanged)
    persona_agent = Agent(
        role="Lead Market Research and Persona Analyst",
        goal=f"Simulate a 1000-person focus group for '{product_idea}'",
        backstory="A world-class market researcher skilled in behavioral insights.",
        llm=main_llm,
        verbose=True,
        allow_delegation=False,
    )
    analyst_agent = Agent(
        role="Senior Product Analyst and Theme Synthesizer",
        goal="Summarize focus group insights into 3–5 strategic product themes.",
        backstory="A data-driven product strategist with deep synthesis skills.",
        llm=main_llm,
        verbose=True,
        allow_delegation=False,
    )

    # (Task definitions are unchanged)
    task_1_feedback = Task(
        description=f"Simulate a focus group for '{product_idea}' and summarize insights.",
        agent=persona_agent,
        expected_output="A multi-paragraph market insights report."
    )
    task_2_themes = Task(
        description="From the focus group report, extract and rank the 3–5 most critical product themes.",
        agent=analyst_agent,
        context=[task_1_feedback],
        expected_output="A numbered list of 3–5 ranked product themes."
    )

    # (Crew definition is unchanged for first 2 tasks)
    blueprint_crew = Crew(
        agents=[persona_agent, analyst_agent],
        tasks=[task_1_feedback, task_2_themes],
        process=Process.sequential,
        verbose=True,
    )

    print(f"--- Starting BLUEPRINT CREW (Tasks 1 & 2) for '{product_idea}' ---")
    crew_result = blueprint_crew.kickoff()
    print(f"--- BLUEPRINT CREW (Tasks 1 & 2) COMPLETE ---")

    # Extract themes list from task 2 output
    raw_themes_output = crew_result.tasks_output[-1].raw
    themes_list = [line.strip() for line in raw_themes_output.split('\n') if line.strip()]

    print(f"--- Starting PM AGENT (Claude Tool Use) ---")
    from core.claude_client import generate_blueprint_with_tools
    tool_output = generate_blueprint_with_tools(product_idea, themes_list)
    print(f"--- PM AGENT COMPLETE ---")

    return BlueprintOutput.model_validate(tool_output)


# --- ================================== ---
# --- 2. ADVERSARIAL CREW (TASK 2) ---
# --- ================================== ---
def run_adversarial_crew(initial_plan: BlueprintOutput) -> Tuple[List[AdversarialUserStory], Dict[str, Any]]:
    """
    Stress-test a product plan under simulated market and technical risks.
    """
    plan_str = initial_plan.model_dump_json(indent=2)

    # (Agent definitions are unchanged)
    market_forecaster = Agent(
        role="Adversarial Market Forecaster",
        goal="Generate 5 realistic market shocks that could threaten this product.",
        backstory="Expert in geopolitical and economic risk analysis.",
        llm=main_llm,
        verbose=True,
        allow_delegation=False,
    )
    cto_agent = Agent(
        role="Adversarial CTO",
        goal="Identify 5 major internal technical risks or scalability issues.",
        backstory="Highly skeptical technical leader who challenges assumptions.",
        llm=main_llm,
        verbose=True,
        allow_delegation=False,
    )
    adaptive_pm = Agent(
        role="Adaptive Crisis Manager",
        goal="Integrate risks into a revised, resilient product plan.",
        backstory="Pragmatic PM skilled in risk adaptation and scenario planning.",
        llm=main_llm,
        verbose=True,
        allow_delegation=False,
    )

    # (Task definitions are unchanged)
    task_1_market_shocks = Task(
        description=f"Analyze the plan: {plan_str}\nList 5 possible market shocks.",
        agent=market_forecaster,
        expected_output="List of 5 market shocks."
    )
    task_2_tech_risks = Task(
        description=f"Analyze the plan: {plan_str}\nList 5 major technical risks.",
        agent=cto_agent,
        expected_output="List of 5 technical risks."
    )
    task_3_adaptive_plan = Task(
        description="""Using all insights, create a 'battle-hardened' plan.
        The plan must include the original user stories, but with new fields or modified descriptions to reflect the identified risks.
        Your final output *must* conform to the 'AdversarialOutput' schema provided.

        The JSON schema for AdversarialOutput is:
        {{
            "stressed_plan": [
                {{
                    "id": "US001",
                    "name": "Original User Story Name",
                    "original_description": "As a user, I want to...",
                    "risk_considerations": "Detailed summary of risks and mitigations.",
                    "impacted_market_shocks": ["shock_id_1", ...],
                    "impacted_technical_risks": ["risk_id_1", ...]
                }},
                ...
            ],
            "premortem_report": {{
                "key_findings": "...",
                "risk_summary": "...",
                ...
            }}
        }}
        """,
        agent=adaptive_pm,
        context=[task_1_market_shocks, task_2_tech_risks],
        expected_output="A JSON object conforming to the 'AdversarialOutput' schema.",
        output_model=AdversarialOutput
    )

    # (Crew definition is unchanged)
    adversarial_crew = Crew(
        agents=[market_forecaster, cto_agent, adaptive_pm],
        tasks=[task_1_market_shocks, task_2_tech_risks, task_3_adaptive_plan],
        process=Process.sequential,
        verbose=True,
    )

    print("--- Starting ADVERSARIAL CREW ---")
    crew_result = adversarial_crew.kickoff()
    print("--- ADVERSARIAL CREW COMPLETE ---")

    # --- THIS IS THE CORRECT FIX ---
    # The raw output from the last task is a JSON string that we parse.
    raw_output = crew_result.tasks_output[-1].raw
    cleaned_output = _clean_json_output(raw_output)
    final_output = AdversarialOutput.model_validate_json(cleaned_output)
    
    # Then we return the clean, structured data
    return final_output.stressed_plan, final_output.premortem_report

def run_summary_agent(stressed_plan: dict, premortem_report: Dict[str, Any]) -> str:
    """
    Runs a single agent to create a non-technical summary of the plan.
    """
    print("--- Starting SUMMARY AGENT ---")
    
    # Get the LLM string
    main_llm = "anthropic/claude-3-5-sonnet-20241022" 
    
    # NOTE: We are converting the report dictionary to a JSON string 
    premortem_str = json.dumps(premortem_report, indent=2)

    # Define the agent
    summary_agent = Agent(
        role="Lead Developer / Engineering Manager",
        goal="Read a technical backlog (a list of user stories) and a risk report, then write a concise, plain-English summary for a non-technical stakeholder.",
        backstory="You are an expert at communicating complex ideas to simple, powerful language. You avoid all technical jargon and focus on the 'what' and 'why'.",
        verbose=True,
        llm=main_llm,
        allow_delegation=False
    )

    # Define the task
    summary_task = Task(
        description=f"""
        You are a Lead Product Manager writing a summary for a stakeholder.
        
        Here is the AI-generated technical backlog:
        {json.dumps(stressed_plan, indent=2)}

        Here is the AI-generated risk analysis (premortem):
        {premortem_str}

        Your task: Write a simple, non-technical summary of this *plan* using **Markdown formatting**.

        Your summary MUST include:
        1.  A "## 💡 Key Features" section, followed by a bulleted list of the 5-6 main work categories.
        2.  A "## ⚠️ Top Identified Risk" section, explaining 2-3 of the biggest risks identified from the premortem in plain English.
        3.  A "## 🚀 First Steps" section, identifying the most important feature to build first.

        Make sure to use **bold text** for emphasis.
        """,
        agent=summary_agent,
        expected_output="A well-formatted Markdown string with headings, bullet points, and bold text."
    )

    # Run the crew (of one)
    summary_crew = Crew(
        agents=[summary_agent],
        tasks=[summary_task],
        process=Process.sequential,
        verbose=True,
    )
    crew_result = summary_crew.kickoff()
    
    print("--- SUMMARY AGENT COMPLETE ---")
    return crew_result.raw