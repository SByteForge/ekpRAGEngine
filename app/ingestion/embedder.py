from typing import List
import ollama
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
 
_client = ollama.Client(host=settings.ollama_base_url)
 
 
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def embed_text(text: str) -> List[float]:
    response = _client.embeddings(model=settings.ollama_embed_model, prompt=text)
    return response["embedding"]
 
 
def embed_batch(texts: List[str]) -> List[List[float]]:
    return [embed_text(t) for t in texts]
