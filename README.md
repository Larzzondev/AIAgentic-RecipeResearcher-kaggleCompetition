# Recipe Researcher – Google Agentic AI Challenge (Capstone) 🏆

Live demo: https://recipe-researcher-2025.web.app

**Endpoint for Kaggle submission:**

POST https://us-central1-recipe-researcher.cloudfunctions.net/agentProxy

Content-Type: application/json

{"query": "pasta carbonara", "constraint": "vegetarian"}

Returns perfect JSON:

```json
{
  "plan": ["step 1", "step 2", "..."],
  "constraint_ack": "Used plant-based bacon alternative",
  "self_corrections": "Removed pancetta, added mushrooms",
  "session_id": "abc123"
}
```

## Architecture

```mermaid
graph TB
    A[User] --> B[Frontend<br/>Pure HTML/CSS/JS]
    B --> C[Firebase Functions<br/>Python 3.12, 512MiB]
    C --> D[Vertex AI Reasoning Engine<br/>Gemini-powered]
    D --> E[OBSERVE → REFLECT → LOOP<br/>Agentic Workflow]
    E --> F[Aggressive JSON Parsing<br/>Guaranteed Valid Output]
    F --> B

    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fce4ec
    style F fill:#e0f2f1
```

```
+-------------------+     +---------------------+
|     Cursor        |     |   Firebase Hosting  |
| (Local Agentic IDE|<--->|   (Frontend UI)     |
+-------------------+     +---------------------+
          ^                       ^
          |                       |
          +----------+------------+
                     |
              +------+------+
              | Vertex AI    |
              | Agent Garden |  <--- CrewAI agents deployed here
              | (Managed)    |
              +------+------+
                     |
        +------------+-------------+
        |            |             |
   +----+----+  +----+----+   +----+----+
   | LangChain| |  Tools  |   | LangSmith|
   +----------+ +---------+   +----------+
                     |
              +------+------+
              | Gemini /     |
              | Grok / etc   |
              +--------------+
```

Frontend: Pure HTML/CSS/JS (no framework)

Backend: Firebase Functions (Gen2, Python 3.12, 512MiB)

Agent: Vertex AI Reasoning Engine (Gemini-powered with OBSERVE→REFLECT→LOOP)

Output: Guaranteed valid JSON via aggressive parsing

Ready for production. No retries. No HTML errors. No crashes.

Made with love (and pain) for the Google Agentic AI Challenge 2025.
