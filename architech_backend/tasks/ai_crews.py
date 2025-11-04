import os
import json
from typing import Tuple
from crewai import Agent, Task, Crew, Process
from core.config import settings  # <-- The missing piece

# --- LLM CONFIGURATION ---
# Set the API key in the environment so CrewAI can find it
os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY
# Defensively remove any stray OpenAI keys
os.environ.pop("OPENAI_API_KEY", None)

# --- YOUR BRILLIANT SOLUTION ---
# This is the simplest, most stable way to define the LLM for CrewAI
google_llm = "gemini/gemini-2.5-flash" 



# --- HELPER FUNCTION ---
def parse_ai_json_output(raw_output: str) -> dict:
    """
    Cleans and parses the AI's string output, returning a valid dictionary.
    Handles code fences like json ... 
    """
    try:
        if "json" in raw_output:
            raw_output = raw_output.split("json")[1].split("```")[0]
        return json.loads(raw_output.strip())
    except Exception as e:
        print(f"ERROR: Failed to parse AI output. Output was: {raw_output}")
        raise ValueError(f"AI returned invalid JSON: {e}")


# --- ============================ ---
# --- 1. BLUEPRINT CREW (TASK 1) ---
# --- ============================ ---
def run_blueprint_crew(product_idea: str) -> dict:
    """
    Runs the initial "Blueprint Crew" to turn a product idea into a developer-ready plan.
    """

    # --- AGENTS ---
    persona_agent = Agent(
        role="Lead Market Research and Persona Analyst",
        goal=f"Simulate a 1000-person focus group for '{product_idea}'",
        backstory="A world-class market researcher skilled in behavioral insights.",
        llm=google_llm,
        verbose=True,
        allow_delegation=False,
    )

    analyst_agent = Agent(
        role="Senior Product Analyst and Theme Synthesizer",
        goal="Summarize focus group insights into 3–5 strategic product themes.",
        backstory="A data-driven product strategist with deep synthesis skills.",
        llm=google_llm,
        verbose=True,
        allow_delegation=False,
    )

    pm_agent = Agent(
        role="Agile Product Manager and User Story Writer",
        goal="Create a developer-ready backlog from the identified product themes.",
        backstory="A highly analytical PM skilled at writing precise user stories.",
        llm=google_llm,
        verbose=True,
        allow_delegation=False,
    )

    # --- TASKS ---
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

    task_3_stories = Task(
        description="""From the prioritized themes, generate a backlog of developer-ready user stories.
        The final output MUST be a single, valid JSON object.""",
        agent=pm_agent,
        context=[task_2_themes],
        expected_output="A JSON object with 'themes' and 'user_stories'."
    )

    # --- CREW ---
    blueprint_crew = Crew(
        agents=[persona_agent, analyst_agent, pm_agent],
        tasks=[task_1_feedback, task_2_themes, task_3_stories],
        process=Process.sequential,
        verbose=True,
        llm=google_llm,
    )

    print(f"--- Starting BLUEPRINT CREW for '{product_idea}' ---")
    crew_result = blueprint_crew.kickoff()
    print(f"--- BLUEPRINT CREW COMPLETE ---")

    return parse_ai_json_output(crew_result.raw)


# --- ================================== ---
# --- 2. ADVERSARIAL CREW (TASK 2) ---
# --- ================================== ---
def run_adversarial_crew(initial_plan: dict) -> Tuple[dict, str]:
    """
    Stress-test a product plan under simulated market and technical risks.
    """
    plan_str = json.dumps(initial_plan, indent=2)

    # --- AGENTS ---
    market_forecaster = Agent(
        role="Adversarial Market Forecaster",
        goal="Generate 5 realistic market shocks that could threaten this product.",
        backstory="Expert in geopolitical and economic risk analysis.",
        llm=google_llm,
        verbose=True,
        allow_delegation=False,
    )

    cto_agent = Agent(
        role="Adversarial CTO",
        goal="Identify 5 major internal technical risks or scalability issues.",
        backstory="Highly skeptical technical leader who challenges assumptions.",
        llm=google_llm,
        verbose=True,
        allow_delegation=False,
    )

    adaptive_pm = Agent(
        role="Adaptive Crisis Manager",
        goal="Integrate risks into a revised, resilient product plan.",
        backstory="Pragmatic PM skilled in risk adaptation and scenario planning.",
        llm=google_llm,
        verbose=True,
        allow_delegation=False,
    )

    # --- TASKS ---
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
        Output MUST be a valid JSON object with 'stressed_plan' and 'premortem_report'.""",
        agent=adaptive_pm,
        context=[task_1_market_shocks, task_2_tech_risks],
        expected_output="A JSON object with 'stressed_plan' (which must contain the original 'user_stories' with added risk analysis) and 'premortem_report'."
    )

    adversarial_crew = Crew(
        agents=[market_forecaster, cto_agent, adaptive_pm],
        tasks=[task_1_market_shocks, task_2_tech_risks, task_3_adaptive_plan],
        process=Process.sequential,
        verbose=True,
        llm=google_llm,
    )

    print("--- Starting ADVERSARIAL CREW ---")
    crew_result = adversarial_crew.kickoff()
    print("--- ADVERSARIAL CREW COMPLETE ---")

    result = parse_ai_json_output(crew_result.raw)
    return result.get("stressed_plan", {}), result.get("premortem_report", "# No report found")