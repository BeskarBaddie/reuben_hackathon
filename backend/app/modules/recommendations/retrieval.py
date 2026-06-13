"""Local document retrieval for grounding agricultural recommendations.

Retrieval runs over a chunked text index (``corpus.jsonl``) produced from the
source PDF corpus by ``ingest.py``. Ranking is semantic (dense) when chunk
embeddings and a local embedding model are available: the query is embedded and
candidates are ranked by cosine similarity. If embeddings or Ollama are
unavailable it falls back to lexical BM25, so the system still runs offline.

Candidates are always hard-filtered to the farm's crop (the corpus is split by
crop); an unsupported crop returns nothing rather than borrowing another crop's
documents. Each passage carries its source PDF path and page so the frontend can
link citations directly to the exact page.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.modules.recommendations.embeddings import embed_text

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
CORPUS_PATH = KNOWLEDGE_DIR / "corpus.jsonl"
EMBEDDINGS_PATH = KNOWLEDGE_DIR / "corpus_embeddings.npy"

# BM25 parameters (standard defaults) for the lexical fallback.
_BM25_K1 = 1.5
_BM25_B = 0.75
_HAZARD_BOOST = 2.0
_IRRIGATION_BOOST = 0.5

_TOKEN_RE = re.compile(r"[a-z]+")
_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "her",
    "was", "one", "our", "out", "use", "with", "this", "that", "from", "they",
    "have", "more", "when", "than", "then", "into", "only", "some", "such",
    "your", "will", "does", "during", "where", "which", "while", "is", "it",
    "to", "of", "in", "on", "or", "a", "an", "as", "at", "be", "by", "do", "if",
    "so", "up",
}

_HAZARD_LEVELS_ACTIVE = {"medium", "high"}


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) > 2 and token not in _STOPWORDS
    ]


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    source: str
    crop: str
    path: str
    page: int
    hazards: tuple[str, ...]
    irrigation: tuple[str, ...]
    text: str
    counts: Counter
    length: int


@dataclass(frozen=True)
class Index:
    documents: tuple[Document, ...]
    doc_freq: dict[str, int]
    avg_len: float


@dataclass
class RetrievedPassage:
    doc_id: str
    title: str
    source: str
    crop: str
    path: str
    page: int
    text: str
    score: float
    vector: np.ndarray | None = None
    tags: dict = field(default_factory=dict)


def _document_from_record(record: dict) -> Document:
    text = record.get("text", "")
    tokens = _tokenize(f"{record.get('source', '')} {text}")
    return Document(
        doc_id=record["doc_id"],
        title=record.get("title", record["doc_id"]),
        source=record.get("source", "unknown"),
        crop=str(record.get("crop", "")).lower(),
        path=record.get("path", ""),
        page=int(record.get("page_start", 0) or 0),
        hazards=tuple(str(h).lower() for h in record.get("hazards", [])),
        irrigation=tuple(str(i).lower() for i in record.get("irrigation", [])),
        text=text,
        counts=Counter(tokens),
        length=len(tokens),
    )


@lru_cache(maxsize=1)
def _load_index() -> Index:
    if not CORPUS_PATH.exists():
        return Index(documents=(), doc_freq={}, avg_len=1.0)

    documents: list[Document] = []
    with CORPUS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                documents.append(_document_from_record(json.loads(line)))

    doc_freq: dict[str, int] = {}
    for document in documents:
        for term in document.counts:
            doc_freq[term] = doc_freq.get(term, 0) + 1
    avg_len = (sum(d.length for d in documents) / len(documents)) if documents else 1.0
    return Index(documents=tuple(documents), doc_freq=doc_freq, avg_len=avg_len or 1.0)


@lru_cache(maxsize=1)
def _load_embeddings() -> np.ndarray | None:
    """Chunk embedding matrix aligned to corpus.jsonl line order, or None."""
    if not EMBEDDINGS_PATH.exists():
        return None
    try:
        matrix = np.load(EMBEDDINGS_PATH)
    except Exception:
        return None
    if matrix.shape[0] != len(_load_index().documents):  # stale vs corpus
        return None
    return matrix.astype(np.float32)


@lru_cache(maxsize=1)
def corpus_crops() -> frozenset[str]:
    """The set of crops the document corpus actually covers."""
    return frozenset(document.crop for document in _load_index().documents if document.crop)


def is_crop_supported(crop: str) -> bool:
    """True if the corpus contains documents for this crop."""
    crop = str(crop or "").strip().lower()
    if not crop:
        return False
    return any(crop == covered or crop in covered for covered in corpus_crops())


@dataclass(frozen=True)
class Query:
    terms: tuple[str, ...]
    crop: str
    irrigation: str
    hazards: frozenset[str]
    text: str


def _evidence_parts(evidence: dict) -> tuple[str, str, set[str], list[str]]:
    farm = evidence.get("farm", {}) or {}
    risk = evidence.get("risk", {}) or {}
    climate = evidence.get("climate", {}) or {}
    forecast = evidence.get("forecast", {}) or {}
    vegetation = evidence.get("vegetation", {}) or {}

    crop = str(farm.get("crop") or "").strip().lower()
    irrigation = str(farm.get("irrigation_type") or "").strip().lower()

    hazards: set[str] = set()
    for hazard in ("drought", "flood", "heat"):
        if str(risk.get(f"{hazard}_level") or "").lower() in _HAZARD_LEVELS_ACTIVE:
            hazards.add(hazard)
    if str(vegetation.get("water_stress") or "").lower() in _HAZARD_LEVELS_ACTIVE:
        hazards.add("drought")
    if not hazards:
        hazards.add("low")

    extras: list[str] = [
        str(climate.get("climate_signal") or ""),
        str(forecast.get("forecast_signal") or ""),
        str(farm.get("farmer_notes") or ""),
    ]
    if "drought" in hazards:
        extras.append("water stress soil moisture irrigation rainfall mulch yield")
    if "flood" in hazards:
        extras.append("waterlogging drainage standing water submergence runoff")
    if "heat" in hazards:
        extras.append("high temperature heat stress tolerance flowering")
    return crop, irrigation, hazards, extras


def build_query_text(evidence: dict) -> str:
    """A natural-language query string for semantic embedding."""
    crop, irrigation, hazards, extras = _evidence_parts(evidence)
    hazard_text = ", ".join(sorted(hazards))
    extras_text = " ".join(part for part in extras if part)
    return (
        f"Climate adaptation guidance for a smallholder {crop or 'crop'} farm "
        f"with {irrigation or 'unknown'} irrigation. Current risks: {hazard_text}. "
        f"{extras_text}"
    ).strip()


def build_query(evidence: dict) -> Query:
    """Turn an evidence snapshot into a retrieval query (terms + text)."""
    crop, irrigation, hazards, extras = _evidence_parts(evidence)
    text_parts = [crop, irrigation, " ".join(hazards), *extras]
    return Query(
        terms=tuple(_tokenize(" ".join(part for part in text_parts if part))),
        crop=crop,
        irrigation=irrigation,
        hazards=frozenset(hazards),
        text=build_query_text(evidence),
    )


def _bm25_score(query_terms: tuple[str, ...], document: Document, index: Index) -> float:
    n_docs = len(index.documents)
    if n_docs == 0:
        return 0.0
    doc_len = document.length or 1
    score = 0.0
    for term in query_terms:
        freq = document.counts.get(term, 0)
        if freq == 0:
            continue
        n_qi = index.doc_freq.get(term, 0)
        idf = math.log(1 + (n_docs - n_qi + 0.5) / (n_qi + 0.5))
        denom = freq + _BM25_K1 * (1 - _BM25_B + _BM25_B * doc_len / index.avg_len)
        score += idf * (freq * (_BM25_K1 + 1)) / denom
    return score


def _matches_crop(query: Query, document: Document) -> bool:
    return bool(query.crop) and (
        document.crop == query.crop or query.crop in document.crop
    )


def _tag_boost(query: Query, document: Document) -> tuple[float, dict]:
    boost = 0.0
    matched: dict = {}
    hazard_hits = sorted(query.hazards.intersection(document.hazards))
    if hazard_hits:
        boost += _HAZARD_BOOST * len(hazard_hits)
        matched["hazards"] = hazard_hits
    if query.irrigation and query.irrigation in document.irrigation:
        boost += _IRRIGATION_BOOST
        matched["irrigation"] = query.irrigation
    return boost, matched


def _passage(document: Document, score: float, vector, tags: dict) -> RetrievedPassage:
    return RetrievedPassage(
        doc_id=document.doc_id,
        title=document.title,
        source=document.source,
        crop=document.crop,
        path=document.path,
        page=document.page,
        text=document.text,
        score=round(float(score), 4),
        vector=vector,
        tags=tags,
    )


def retrieve(evidence: dict, top_k: int = 4, max_per_source: int = 2) -> list[RetrievedPassage]:
    """Return the top-k guidance passages most relevant to the evidence.

    Ranks by semantic similarity (dense embeddings) when available, otherwise by
    BM25. Candidates are restricted to the farm's crop; no more than
    ``max_per_source`` chunks come from any single source document.
    """
    index = _load_index()
    if not index.documents:
        return []

    query = build_query(evidence)
    candidates = [
        (position, document)
        for position, document in enumerate(index.documents)
        if _matches_crop(query, document)
    ]
    if not candidates:
        return []

    embeddings = _load_embeddings()
    query_vector = embed_text(query.text) if embeddings is not None else None

    scored: list[RetrievedPassage] = []
    if embeddings is not None and query_vector is not None:
        # Dense semantic ranking by cosine similarity (vectors are normalised).
        for position, document in candidates:
            vector = embeddings[position]
            similarity = float(vector @ query_vector)
            scored.append(
                _passage(document, similarity, vector, {"method": "dense", "cosine": round(similarity, 4)})
            )
    else:
        # Lexical BM25 fallback.
        for _, document in candidates:
            lexical = _bm25_score(query.terms, document, index)
            if lexical <= 0:
                continue
            boost, matched = _tag_boost(query, document)
            scored.append(
                _passage(
                    document,
                    lexical + boost,
                    None,
                    {"method": "bm25", "matched": matched, "lexical": round(lexical, 4)},
                )
            )

    scored.sort(key=lambda passage: (-passage.score, passage.doc_id))

    # Diversify: cap how many chunks come from any one source document.
    selected: list[RetrievedPassage] = []
    per_source: dict[str, int] = {}
    for passage in scored:
        if per_source.get(passage.source, 0) >= max_per_source:
            continue
        selected.append(passage)
        per_source[passage.source] = per_source.get(passage.source, 0) + 1
        if len(selected) >= top_k:
            break
    return selected


def format_context(passages: list[RetrievedPassage]) -> str:
    """Render retrieved passages into a grounding context block for the model."""
    if not passages:
        return "No specific guidance documents were retrieved for this farm."
    blocks = []
    for number, passage in enumerate(passages, start=1):
        blocks.append(f"[{number}] {passage.title} (source: {passage.source})\n{passage.text}")
    return "\n\n".join(blocks)


def citations_from_passages(passages: list[RetrievedPassage]) -> list[dict]:
    """Truthful citation list built from the passages actually retrieved."""
    return [
        {
            "doc_id": passage.doc_id,
            "title": passage.title,
            "source": passage.source,
            "path": passage.path,
            "page": passage.page,
        }
        for passage in passages
    ]
