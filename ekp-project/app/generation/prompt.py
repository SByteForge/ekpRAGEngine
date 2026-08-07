from typing import List, Dict

def construct_prompt(user_query: str, context: List[str], max_length: int = 512) -> str:
    """
    Constructs a prompt for the language model based on the user query and context.

    Args:
        user_query (str): The user's question or query.
        context (List[str]): A list of context strings to include in the prompt.
        max_length (int): The maximum length of the prompt.

    Returns:
        str: The constructed prompt.
    """
    context_str = "\n".join(context)
    prompt = f"User Query: {user_query}\n\nContext:\n{context_str}\n\nResponse:"
    
    # Truncate the prompt if it exceeds the maximum length
    if len(prompt) > max_length:
        prompt = prompt[:max_length]

    return prompt

def format_response(response: str) -> Dict[str, str]:
    """
    Formats the response from the language model into a structured dictionary.

    Args:
        response (str): The raw response from the language model.

    Returns:
        Dict[str, str]: A dictionary containing the formatted response.
    """
    return {
        "generated_text": response.strip()
    }