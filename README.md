# DoesItExist - Invention Checker Agent

This project is an AI agent that accepts a user's invention idea, dynamically decides what tools to run, and returns whether the idea already exists based on patent, academic, and web data.

## Stack

- **Backend**: Python + FastAPI
- **AI Agent Engine**: LangGraph (Agent Mode)
- **LLM**: OpenAI GPT-4o
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector DB**: Pinecone
- **Web Search**: Tavily AI
- **Patent Search**: PatentsView
- **Scholar Search**: Semantic Scholar

## Requirements

- Python 3.10–3.13 (Python 3.14 currently emits warnings from Pydantic/LangChain)
- An OpenAI API key with access to GPT-4o
- Accounts/API keys for Tavily, PatentsView, and Semantic Scholar

## Setup

1. Clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # macOS / Linux
   source venv/bin/activate
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the project root and add the required secrets:

   | Variable | Required | Description |
   | --- | --- | --- |
   | `OPENAI_API_KEY` | ✅ | Used for GPT-4o chats and embeddings |
   | `TAVILY_API_KEY` | ✅ | Web search results + metadata |
   | `PATENTSVIEW_API_KEY` | ✅ | Patent search API access |
   | `SEMANTIC_SCHOLAR_API_KEY` | ✅ | Academic paper search |
   | `LANGCHAIN_API_KEY`, `LANGCHAIN_ENDPOINT` | optional | Only if you want LangSmith tracing |
   | `LANGCHAIN_TRACING_V2`, `LANGCHAIN_PROJECT` | optional | LangSmith project metadata |

   > Tip: `python -c "import secrets; print(secrets.token_urlsafe(32))"` is handy for generating placeholder values when testing locally.

## Running the application

Start the FastAPI server (hot reload for development):

```bash
.\venv\Scripts\python -m uvicorn main:app --reload
# or
python -m uvicorn main:app --reload
```

The project serves a minimal frontend at `http://127.0.0.1:8000`. To exercise the backend directly, send a POST request to `/check`:

```bash
curl -X POST http://127.0.0.1:8000/check ^
     -H "Content-Type: application/json" ^
     -d "{\"idea\": \"A coffee mug that keeps the coffee at the perfect temperature\"}"
```

Successful responses contain the agent's verdict (Likely original / Possibly overlapping / Clearly already existing) plus supporting evidence pulled from the tool chain.
