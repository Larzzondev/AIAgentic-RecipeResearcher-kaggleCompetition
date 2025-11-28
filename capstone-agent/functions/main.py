import os
import json
import uuid
import textwrap

from firebase_functions import https_fn, options
from firebase_admin import initialize_app
from google.auth.transport.requests import AuthorizedSession
import google.auth

initialize_app()

# Base URL for the Vertex AI Agent Engine REST API
_API_BASE_URL = "https://us-central1-aiplatform.googleapis.com/v1/"


# Note: The Agent requires the input to be formatted with OBSERVE/REFLECT/LOOP headers.
def _format_agent_message(query: str, constraint: str, session_id: str) -> str:
    """Formats the user input into the multi-part prompt expected by RecipeLoopAgent."""
    constraint_section = constraint if constraint else "No additional constraint."

    # Matches the logic from RecipeLoopAgent in agent_deploy.py
    # Includes the CRITICAL instruction to force JSON output
    return textwrap.dedent(
        f"""
        SESSION_ID: {session_id}

        OBSERVE:
        - Capture the incoming request exactly as received.
        - Request: "{query}"
        - Constraint: "{constraint_section}"

        REFLECT:
        - Review the observation for missing context (missing steps, conflicting instructions).
        - Call out any tensions or nutrition trade-offs before planning.

        LOOP:
        - Produce a corrected cooking plan that explicitly mentions how you honored the constraint.
        - Highlight a single self-correction you made after your reflection.
        - **The ONLY output you provide MUST be a valid, unadulterated JSON object.**
        - Answer in JSON with keys: plan (array of steps), constraint_ack (string), self_corrections (string), session_id (string).
        - Close the loop by confirming the plan is ready to execute.
        """
    ).strip()

@https_fn.on_request(memory=options.MemoryOption.MB_512, max_instances=1)
def agentProxy(req: https_fn.Request) -> https_fn.Response:
    # Handle CORS preflight requests
    if req.method == "OPTIONS":
        return https_fn.Response("", headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        })

    if req.method != "POST":
        return https_fn.Response("Method Not Allowed", status=405)

    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
    }

    payload = req.get_json(silent=True)
    if not payload or not all(k in payload for k in ["query", "constraint"]):
        return https_fn.Response(
            json.dumps({"error": "Missing 'query' or 'constraint' in JSON body."}),
            status=400,
            headers=headers,
        )

    query = payload["query"]
    constraint = payload["constraint"]

    # 1. Retrieve Agent Endpoint (Must be set as env var: VERTEX_AGENT_ID)
    AGENT_ENDPOINT = os.environ.get("VERTEX_AGENT_ID")

    if not AGENT_ENDPOINT:
        return https_fn.Response(
            json.dumps({"error": "Configuration Error: Agent ID environment variable (VERTEX_AGENT_ID) not set. Check deployment command."}),
            status=500,
            headers=headers,
        )

    # Construct the correct API URL for the Reasoning Engine query method
    API_URL = f"{_API_BASE_URL}{AGENT_ENDPOINT}:query"

    # 2. Prepare for invoking Vertex AI Agent with IAM credentials
    # Credentials are automatically derived from the Firebase Function's service account.
    credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    session = AuthorizedSession(credentials)

    # 3. Format the message and build request body
    session_id = str(uuid.uuid4())
    formatted_message = _format_agent_message(query, constraint, session_id)

    # This is the JSON payload structure required by the Agent Engine REST API
    request_body = {
        "input": {
            "message": formatted_message,
            "session_id": session_id
        }
    }

    print(f"Calling Agent Engine: {API_URL}")

    try:
        # 4. Make the secure REST API Call (HTTP POST)
        response = session.post(
            API_URL,
            json=request_body
        )

        response.raise_for_status()  # Raises an exception for HTTP errors (4xx, 5xx)

        # 5. Process the response with Robust JSON Extraction
        response_data = response.json()

        # Extract the output from the response
        if 'output' in response_data:
            output = response_data['output']

            # CRITICAL FIX: Aggressively search for the JSON block to ignore conversational text
            try:
                if isinstance(output, str):
                    # Find the start of the JSON object (first '{')
                    start_index = output.find('{')
                    # Find the end of the JSON object (last '}')
                    end_index = output.rfind('}')

                    if start_index != -1 and end_index != -1 and end_index > start_index:
                        # Extract only the JSON substring
                        json_string = output[start_index : end_index + 1]
                        agent_json = json.loads(json_string)
                    else:
                        # If we can't find a JSON block, trigger the fallback text response
                        raise json.JSONDecodeError("JSON block not found in agent output", output, 0)
                else:
                    agent_json = output

                # Successful JSON parse, return the clean JSON to the client
                return https_fn.Response(
                    json.dumps(agent_json),
                    headers=headers,
                    status=200
                )
            except (json.JSONDecodeError, TypeError):
                # Fallback: If stripping failed, return a JSON object with the full, unparsable text output
                return https_fn.Response(
                    json.dumps({
                        "response": str(output),
                        "note": "Agent returned unparsable text response"
                    }),
                    headers=headers,
                    status=200
                )
        else:
            return https_fn.Response(
                json.dumps({
                    "response": str(response_data),
                    "note": "Unexpected response format from agent"
                }),
                headers=headers,
                status=200
            )

    except Exception as e:
        # Catch network/API errors and return a JSON error to the client
        print(f"API Call to Agent Engine failed: {e}")
        error_response = {
            "error": "Failed to call Vertex AI Agent Engine.",
            "details": str(e),
            "api_url": API_URL
        }
        # Include API response text for debugging if available
        if 'response' in locals():
            error_response['api_response'] = response.text

        return https_fn.Response(
            json.dumps(error_response),
            status=500,
            headers=headers
        )
