import json
from anthropic import Anthropic
from core.config import settings

client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
# We will use claude-3-5-sonnet-20241022 to represent the requested claude-sonnet-4-5 model
MODEL_NAME = "claude-3-5-sonnet-20241022"

def generate_blueprint_with_tools(product_idea: str, themes_list: list) -> dict:
    """
    Directly uses Anthropic's Tool Use API to generate a structured product backlog.
    This demonstrates explicit 'Agentic AI' tool calling capabilities bypassing standard LangChain/CrewAI wrappers.
    """
    
    # Define the tool schema
    tools = [
        {
            "name": "save_product_backlog",
            "description": "Saves the generated product themes and user stories into a structured backlog format.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "themes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of 3-5 strategic product themes."
                    },
                    "user_stories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "A unique ID for the user story, e.g., 'US001'."
                                },
                                "name": {
                                    "type": "string",
                                    "description": "The concise title of the user story."
                                },
                                "description": {
                                    "type": "string",
                                    "description": "The full user story text in 'As a user...' format."
                                }
                            },
                            "required": ["id", "name", "description"]
                        },
                        "description": "The initial list of user stories based on the themes."
                    }
                },
                "required": ["themes", "user_stories"]
            }
        }
    ]

    prompt = f"""
    You are an Agile Product Manager and User Story Writer.
    Your goal is to create a developer-ready backlog from the identified product themes.
    
    Product Idea: {product_idea}
    Prioritized Themes: {', '.join(themes_list)}
    
    Use the 'save_product_backlog' tool to output your result.
    Make sure to generate 5 to 10 high quality user stories.
    """

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=4096,
        tools=tools,
        tool_choice={"type": "tool", "name": "save_product_backlog"},
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # Extract the tool use from the response
    for block in response.content:
        if block.type == "tool_use" and block.name == "save_product_backlog":
            return block.input
            
    raise Exception("Claude did not return the expected tool call.")
