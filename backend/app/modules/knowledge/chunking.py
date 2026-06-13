import hashlib
import re


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, max_words: int = 450, overlap_words: int = 70) -> list[str]:
    normalized = normalize_text(text)
    words = normalized.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(0, end - overlap_words)
    return chunks


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def infer_metadata(source_name: str, text: str) -> dict[str, str | None]:
    haystack = f"{source_name}\n{text[:2000]}".lower()
    crops = ["maize", "corn", "rice", "beans", "sorghum", "wheat", "cassava", "millet"]
    topics = {
        "drought": ["drought", "dry spell", "water stress", "moisture"],
        "flood": ["flood", "waterlogging", "standing water", "drainage"],
        "heat": ["heat", "temperature", "hot", "heat stress"],
        "fertilizer": ["fertilizer", "nitrogen", "top dressing", "manure"],
        "pest": ["pest", "disease", "fungus", "insect"],
        "irrigation": ["irrigation", "watering", "water source"],
    }

    crop = next((item for item in crops if item in haystack), None)
    if crop == "corn":
        crop = "maize"

    topic = None
    for candidate, terms in topics.items():
        if any(term in haystack for term in terms):
            topic = candidate
            break

    return {"crop": crop, "topic": topic, "region": None}
