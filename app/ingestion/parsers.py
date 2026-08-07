from pathlib import Path
from typing import List, Tuple
from pypdf import PdfReader
import docx
 
 
def parse_pdf(path: Path) -> List[Tuple[str, int]]:
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((text, i + 1))
    return pages
 
 
def parse_markdown(path: Path) -> List[Tuple[str, int]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [(text, None)] if text.strip() else []
 
 
def parse_docx(path: Path) -> List[Tuple[str, int]]:
    document = docx.Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
    return [(text, None)] if text.strip() else []
 
 
PARSERS = {".pdf": parse_pdf, ".md": parse_markdown, ".markdown": parse_markdown, ".docx": parse_docx}
 
 
def parse_document(path: Path) -> List[Tuple[str, int]]:
    ext = path.suffix.lower()
    if ext not in PARSERS:
        raise ValueError(f"Unsupported doc type '{ext}' - v1 supports {list(PARSERS.keys())}")
    return PARSERS[ext](path)
