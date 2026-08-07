import json
import re
from typing import List
import ollama
from app.core.config import settings

_client = ollama.Client(host=settings.ollama_base_url)

JUDGE_PROMPT_TEMPLATE = """You are an evaluation judge. Given a question, a set of \
source excerpts, and a generated answer, assess whether the answer is faithful to \
(i.e. fully supported by) the source excerpts.

Respond with ONLY a JSON object, no other text, in this exact format:
{{"faithfulness_score": <float 0.0-1.0>, "hallucination": <true|false>, "reasoning": "<one short sentence>"}}

faithfulness_score: 1.0 = every claim in the answer is directly supported by the excerpts.
0.0 = the answer is entirely unsupported or contradicts the excerpts.
hallucination: true if the answer states any specific fact NOT present in the excerpts.

--- SOURCE EXCERPTS ---
{sources}
--- END SOURCE EXCERPTS ---

Question: {question}

Generated Answer: {answer}

JSON response:"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in judge response: {text[:200]}")
    return json.loads(match.group(0))


def judge_faithfulness(question: str, answer: str, source_chunks: List[dict]) -> dict:
    sources_text = "\n\n".join(f"[{i+1}] {c['text'][:400]}" for i, c in enumerate(source_chunks))
    prompt = JUDGE_PROMPT_TEMPLATE.format(sources=sources_text, question=question, answer=answer)
    try:
        response = _client.generate(model=settings.ollama_judge_model, prompt=prompt, stream=False)
        parsed = _extract_json(response["response"])
        return {
            "faithfulness_score": float(parsed.get("faithfulness_score", 0.0)),
            "hallucination": bool(parsed.get("hallucination", True)),
            "reasoning": parsed.get("reasoning", ""),
            "judge_success": True, "judge_error": None,
        }
    except Exception as e:
        return {
            "faithfulness_score": None, "hallucination": None, "reasoning": None,
            "judge_success": False, "judge_error": f"{type(e).__name__}: {e}",
        }
