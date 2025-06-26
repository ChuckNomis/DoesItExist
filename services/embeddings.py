from openai import AsyncOpenAI
import os


async def get_embedding(text: str, model="text-embedding-3-small"):
    """
    Generates an embedding for a given text using OpenAI's async API.
    """
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    text = text.replace("\n", " ")
    try:
        response = await client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        print(f"An error occurred while generating embedding: {e}")
        return None
