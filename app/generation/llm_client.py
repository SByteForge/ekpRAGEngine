import ollama
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings

_client = ollama.Client(host=settings.ollama_base_url)


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=6))
def generate(prompt: str, model: str = None) -> str:
    model = model or settings.ollama_gen_model
    response = _client.generate(model=model, prompt=prompt, stream=False)
    return response["response"]
