from typing import List
from app.retrieval.dense import RetrievedChunk

SYSTEM_PROMPT = """You are an internal knowledge assistant. Answer the user's \
question using ONLY the numbered source excerpts provided below. \
Cite sources inline using [N] notation matching the excerpt numbers. \
If the excerpts do not contain enough information to answer, say so explicitly \
rather than guessing or using outside knowledge. Do not fabricate citations."""


def build_prompt(question: str, chunks: List[RetrievedChunk]) -> str:
    sources_block = "\n\n".join(
        f"[{i+1}] (source: {c.filename}, page {c.page_number or 'n/a'})\n{c.text}"
        for i, c in enumerate(chunks)
    )
    return f"""{SYSTEM_PROMPT}

--- SOURCE EXCERPTS ---
{sources_block}
--- END SOURCE EXCERPTS ---

Question: {question}

Answer (cite sources as [1], [2], etc.):"""
