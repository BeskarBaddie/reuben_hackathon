"""Ingest the source PDF corpus into a chunked text index for retrieval.

Run manually whenever the documents under ``backend/data/rag_sources`` change::

    python -m app.modules.recommendations.knowledge.ingest

It extracts text from each PDF (locally, via ``pypdf``), splits it into
overlapping word-window chunks, tags each chunk with the crop (from the source
folder) and any climate hazards it mentions, and writes ``corpus.jsonl`` next to
this script. ``retrieval.py`` loads that file; the app never parses PDFs at
request time.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).parent
SOURCE_DIR = Path(__file__).resolve().parents[4] / "data" / "rag_sources"
CORPUS_PATH = HERE / "corpus.jsonl"

CHUNK_WORDS = 180
CHUNK_OVERLAP = 30
MIN_CHUNK_WORDS = 40

HAZARD_KEYWORDS = {
    "drought": (
        "drought", "water stress", "moisture stress", "dry spell", "water deficit",
        "rainfall deficit", "water scarcity", "soil moisture",
    ),
    "flood": (
        "flood", "waterlog", "submergence", "standing water", "excess water",
        "drainage", "saturated soil",
    ),
    "heat": (
        "heat stress", "high temperature", "heat tolerance", "temperature stress",
        "extreme heat", "thermal stress",
    ),
}

_WS_RE = re.compile(r"\s+")
_TITLE_CLEAN_RE = re.compile(r"[_\-]+")


def _clean_title(stem: str) -> str:
    title = _TITLE_CLEAN_RE.sub(" ", stem)
    title = _WS_RE.sub(" ", title).strip()
    return title


def _normalise(text: str) -> str:
    text = text.replace("­", "")  # soft hyphen
    text = re.sub(r"-\n", "", text)  # join hyphenated line breaks
    return _WS_RE.sub(" ", text).strip()


def _detect_hazards(text: str) -> list[str]:
    lowered = text.lower()
    return [
        hazard
        for hazard, keywords in HAZARD_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]


def _chunk_pages(pages: list[str]) -> list[dict]:
    """Chunk a document into overlapping word windows, tracking page spans."""
    words: list[str] = []
    word_pages: list[int] = []
    for page_number, page_text in enumerate(pages, start=1):
        for word in page_text.split():
            words.append(word)
            word_pages.append(page_number)

    chunks: list[dict] = []
    step = CHUNK_WORDS - CHUNK_OVERLAP
    for start in range(0, len(words), step):
        window = words[start : start + CHUNK_WORDS]
        if len(window) < MIN_CHUNK_WORDS:
            continue
        span_pages = word_pages[start : start + CHUNK_WORDS]
        chunks.append(
            {
                "text": " ".join(window),
                "page_start": span_pages[0],
                "page_end": span_pages[-1],
            }
        )
    return chunks


def ingest() -> None:
    if not SOURCE_DIR.exists():
        raise SystemExit(f"Source directory not found: {SOURCE_DIR}")

    records: list[dict] = []
    pdf_paths = sorted(SOURCE_DIR.rglob("*.pdf"))
    for pdf_path in pdf_paths:
        crop = pdf_path.parent.name.strip().lower()
        title = _clean_title(pdf_path.stem)
        try:
            reader = PdfReader(str(pdf_path))
            pages = [_normalise(page.extract_text() or "") for page in reader.pages]
        except Exception as error:  # noqa: BLE001 - report and skip unreadable PDFs
            print(f"  ! skipped {pdf_path.name}: {error}")
            continue

        chunks = _chunk_pages(pages)
        for index, chunk in enumerate(chunks):
            page_start = chunk["page_start"]
            page_end = chunk["page_end"]
            page_label = (
                f"p. {page_start}" if page_start == page_end else f"pp. {page_start}-{page_end}"
            )
            records.append(
                {
                    "doc_id": f"{pdf_path.stem}__{index:04d}",
                    "title": f"{title} ({page_label})",
                    "source": title,
                    "crop": crop,
                    "page_start": page_start,
                    "page_end": page_end,
                    "hazards": _detect_hazards(chunk["text"]),
                    "irrigation": ["none", "rainfed", "partial", "full"],
                    "text": chunk["text"],
                }
            )
        print(f"  {pdf_path.relative_to(SOURCE_DIR)} -> {len(chunks)} chunks ({crop})")

    with CORPUS_PATH.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    crops = sorted({record["crop"] for record in records})
    print(f"\nWrote {len(records)} chunks from {len(pdf_paths)} PDFs to {CORPUS_PATH.name}")
    print(f"Crops: {', '.join(crops)}")


if __name__ == "__main__":
    ingest()
