def chunk_text(text: str, chunk_size: int = 8000, overlap: int = 500) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
        split_at = text.rfind("\n\n", start, end)
        if split_at <= start:
            split_at = text.rfind(". ", start, end)
        if split_at <= start:
            split_at = text.rfind(" ", start, end)
        if split_at <= start:
            split_at = end
        else:
            split_at += 1
        chunks.append(text[start:split_at])
        start = split_at - overlap
        if start < 0:
            start = 0
    return chunks
