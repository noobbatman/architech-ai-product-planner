import json
from trello import TrelloClient

def create_trello_board(api_key: str, api_token: str, project_name: str, plan_dict: dict, report_str: str) -> str:
    """
    Creates a new Trello board and populates it with lists and cards from the AI's plan.
    """
    try:
        print(f"--- TRELLO BOT: DEBUG: Received plan of type: {type(plan_dict)} ---")
        
        client = TrelloClient(api_key=api_key, token=api_token)
        
        print(f"--- TRELLO BOT: Creating board named: '{project_name}' ---")

        # --- FIX for 400 Bad Request (Description too long) ---
        max_len = 16000 
        if len(report_str) > max_len:
            truncated_desc = report_str[:max_len] + "\n\n... (Report truncated due to Trello size limit)"
        else:
            truncated_desc = report_str
            
        # --- FIX for 'description' keyword error ---
        board = client.add_board(project_name, default_lists=False)
        board.set_description(truncated_desc)

        # --- Create standard agile lists ---
        list_backlog = board.add_list("Backlog (from AI)")
        list_todo = board.add_list("To Do")
        list_doing = board.add_list("Doing")
        list_done = board.add_list("Done")
        list_risks = board.add_list("Simulated Risks ⚠️")
        
        # --- FIX: The AI plan *is* the list of stories ---
        if isinstance(plan_dict, list):
            stories = plan_dict
        else:
            stories = plan_dict.get("user_stories", []) # Fallback

        if not stories:
            print("--- TRELLO BOT: No 'user_stories' found in plan (or plan was not a list). ---")
            list_backlog.add_card("Error: AI plan did not contain user stories.")
            return board.url
        
        print(f"--- TRELLO BOT: DEBUG: The first story object looks like this: {stories[0]} ---")

        # ---
        # --- FINAL ROBUST PARSING LOOP ---
        # ---
        
        for story in stories:
            # This 'story' is a dict. We need to find the title and description.
            
            # --- 1. Robust Title Finder ---
            # We'll search for the most likely keys in order of preference.
            name = "Missing Title" # Default
            possible_title_keys = ["name", "title", "story", "description"]
            
            for key in possible_title_keys:
                if story.get(key) and isinstance(story[key], str):
                    name = story[key]
                    # If we find 'name' or 'title', it's almost certainly the intended title.
                    if key in ["name", "title"]:
                        break
            
            # --- 2. Robust Description Builder ---
            desc_parts = []
            
            # Iterate over *all* keys to find description/risk info
            for key, value in story.items():
                key_lower = key.lower()
                
                # Skip the key we *already used* as the title, and skip IDs
                if key in possible_title_keys and value == name:
                    continue
                if key_lower == "id":
                    continue

                # Add everything else, formatting "risk" keys nicely
                if "risk" in key_lower or "mitigation" in key_lower or "impact" in key_lower or "priority" in key_lower:
                    header = key.replace('_', ' ').title()
                    desc_parts.append(f"**⚠️ {header}:**")
                    
                    if isinstance(value, list):
                        for item in value:
                            desc_parts.append(f"- {item}")
                    else:
                        desc_parts.append(str(value))
                    desc_parts.append("\n")
                
                # Also add "original_description" if it exists and wasn't the title
                elif "description" in key_lower:
                    desc_parts.append(f"**Description:**\n{value}\n")

            desc = "\n".join(desc_parts)

            list_backlog.add_card(name=name, desc=desc)

        # --- END OF ROBUST LOOP ---

        print(f"--- TRELLO BOT: Added {len(stories)} story cards to Backlog. ---")

        return board.url

    except Exception as e:
        print(f"--- TRELLO BOT ERROR: Failed to create board. Error: {e} ---")
        return "https://trello.com/b/failed-to-create"