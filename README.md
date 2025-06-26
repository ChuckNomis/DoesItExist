# IsExist - Invention Checker Agent

This project is an AI agent that accepts a user's invention idea, dynamically decides what tools to run, and returns whether the idea already exists, based on patent, product, and web data.

## Stack

- **Backend**: Python + FastAPI
- **AI Agent Engine**: LangGraph (Agent Mode)
- **LLM**: OpenAI GPT-4o
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector DB**: Pinecone
- **Web Search**: Tavily AI
- **Patent Search**: Google Patents / Lens.org (scrape or API)
- **Product Search**: Product Hunt, Kickstarter, Amazon (API/scrape)

## Setup

1.  Clone the repository.
2.  Create a virtual environment: `python -m venv venv`
3.  Activate the virtual environment: `source venv/bin/activate` (on Unix/macOS) or `venv\Scripts\activate` (on Windows).
4.  Install the dependencies: `pip install -r requirements.txt`
5.  Create a `.env` file and add your API keys for OpenAI, SerpAPI, and Pinecone. See `.env.example`.

## Running the application

Run the FastAPI server:

```bash
uvicorn main:app --reload
```

Then, you can send a POST request to `http://127.0.0.1:8000/check` with a JSON body like:

```json
{
  "idea": "A coffee mug that keeps the coffee at the perfect temperature"
}
```
