from dataclasses import dataclass
from typing import List, Optional, Tuple
import tiktoken
from app.core.config import settings
 
_encoder = tiktoken.get_encoding("cl100k_base")
 
 
@dataclass
class Chunk:
    text: str
    chunk_index: int
    token_count: int
    page_number: Optional[int]
 
 
def chunk_pages(pages, chunk_size: int = None, overlap: int = None) -> List[Chunk]:
    chunk_size = chunk_size or settings.chunk_size_tokens
    overlap = overlap or settings.chunk_overlap_tokens
    chunks: List[Chunk] = []
    idx = 0
    for text, page_number in pages:
        tokens = _encoder.encode(text)
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = _encoder.decode(chunk_tokens)
            chunks.append(Chunk(text=chunk_text, chunk_index=idx, token_count=len(chunk_tokens), page_number=page_number))
            idx += 1
            if end == len(tokens):
                break
            start = end - overlap
    return chunks
