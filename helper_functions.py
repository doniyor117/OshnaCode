def truncate_output(text: str, max_chars: int = 10000) -> str:
    """
    Truncates massive tool outputs to protect the context window.
    Returns the first half and the last half of the output.
    """
    if len(text) <= max_chars:
        return text
    
    half = max_chars // 2
    return f"{text[:half]}\n\n... [TRUNCATED: {len(text) - max_chars} characters omitted by context manager] ...\n\n{text[-half:]}"

