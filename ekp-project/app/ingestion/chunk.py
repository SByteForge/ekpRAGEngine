from typing import List

def chunk_document(document: str, chunk_size: int) -> List[str]:
    """
    Splits a document into chunks of specified size.

    Args:
        document (str): The document to be chunked.
        chunk_size (int): The maximum size of each chunk.

    Returns:
        List[str]: A list of document chunks.
    """
    return [document[i:i + chunk_size] for i in range(0, len(document), chunk_size)]

def process_chunks(chunks: List[str]) -> List[str]:
    """
    Processes a list of document chunks.

    Args:
        chunks (List[str]): The list of chunks to process.

    Returns:
        List[str]: A list of processed chunks.
    """
    # Placeholder for processing logic (e.g., embedding, indexing)
    processed_chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
    return processed_chunks