import re

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    # Replace separators with spaces
    text = re.sub(r"[_\-.]", " ", text)
    # Remove bracketed content (often tags or channel names)
    text = re.sub(r"\[.*?\]", "", text)
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()
