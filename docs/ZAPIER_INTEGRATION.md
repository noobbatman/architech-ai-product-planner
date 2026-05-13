# Zapier Integration Guide for ArchiTECH

ArchiTECH is designed to be the "Agentic AI Brain" in your existing business workflows. By utilizing Zapier, you can pipe ideas in from any tool and send structured backlogs out to your team's preferred project management software.

## The ArchiTECH Zapier Endpoints

1. **Trigger Endpoint (Input):** `POST /api/v1/trigger`
   - Accepts: `{"initial_idea": "Your product idea", "zapier_webhook_url": "https://hooks.zapier.com/..."}`
   - Returns: `{"job_id": "uuid"}`
2. **Webhook (Output):** The URL you provide in `zapier_webhook_url` will receive an async POST request when the AI finishes generating the backlog.
   - Payload: `{"project_id": "...", "idea": "...", "themes": [...], "user_stories": [...], "trello_board_url": "..."}`

---

## Example Flow 1: Google Sheets → ArchiTECH → Jira

Automate your backlog creation straight from a product idea repository in Google Sheets.

### Step 1: The Input Trigger (Zap 1)
1. **Trigger:** Choose "Google Sheets" and select "New Spreadsheet Row".
2. **Action:** Choose "Webhooks by Zapier" and select "Custom Request".
3. **Setup:**
   - **Method:** POST
   - **URL:** `https://your-architech-url.com/api/v1/trigger`
   - **Data:** 
     ```json
     {
       "initial_idea": "{{Sheet.IdeaColumn}}",
       "zapier_webhook_url": "INSERT_WEBHOOK_URL_FROM_ZAP_2"
     }
     ```

*(Screenshot: Google Sheets Setup)*

### Step 2: The Output Receiver (Zap 2)
1. **Trigger:** Choose "Webhooks by Zapier" and select "Catch Hook".
   - *Copy this webhook URL and paste it into Zap 1.*
2. **Action 1 (Format):** Add a "Looping by Zapier" step to iterate over the `user_stories` array received from ArchiTECH.
3. **Action 2 (Jira):** Choose "Jira Software" and select "Create Issue".
   - Map the `Summary` to `user_stories.name`.
   - Map the `Description` to `user_stories.description` + `user_stories.risk_considerations`.

*(Screenshot: Jira Setup)*

---

## Example Flow 2: Typeform → ArchiTECH → Slack + Notion

Great for design agencies receiving client briefs.

### Step 1: The Input Trigger (Zap 1)
1. **Trigger:** Choose "Typeform" and select "New Entry".
2. **Action:** Choose "Webhooks by Zapier" and select "POST".
   - Send the Typeform response to ArchiTECH's `/api/v1/trigger` endpoint with Zap 2's Webhook URL.

*(Screenshot: Typeform Setup)*

### Step 2: The Output Receiver (Zap 2)
1. **Trigger:** "Webhooks by Zapier" (Catch Hook).
2. **Action 1 (Slack):** Choose "Slack" -> "Send Channel Message".
   - Message: "New Product Plan ready for {{idea}}! Themes identified: {{themes}}. View Trello: {{trello_board_url}}"
3. **Action 2 (Notion):** Choose "Notion" -> "Create Database Item".
   - Save the raw JSON payload to a central "Client Plans" database for internal review.

*(Screenshot: Slack Notion Setup)*
