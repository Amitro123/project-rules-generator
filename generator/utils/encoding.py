"""Encoding utilities for cleaning mojibake and encoding artifacts."""


def normalize_mojibake(text: str) -> str:
    """Clean encoding artifacts from text while preserving legitimate characters.
    
    This function applies targeted replacements for known mojibake sequences
    that occur due to encoding mismatches, especially on Windows terminals.
    
    Args:
        text: Input text that may contain encoding artifacts
        
    Returns:
        Cleaned text with mojibake replaced by correct characters
        
    Note:
        This does NOT remove legitimate Hebrew or other Unicode characters.
        Only known bad sequences are replaced.
    """
    if not text:
        return text
    
    # Apply targeted replacements for known mojibake sequences
    # Handle both literal string and Unicode character sequence
    # ג€" (U+05D2 U+20AC U+201D) is a corrupted em-dash (—) from UTF-8 encoding issues
    cleaned = text.replace('\u05d2\u20ac\u201d', '\u2014')  # Unicode sequence
    cleaned = cleaned.replace('ג€"', '—')  # Literal string (for files)
    
    # Additional known mojibake patterns can be added here
    # Example: cleaned = cleaned.replace('â€™', "'")
    
    return cleaned
