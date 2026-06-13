"""Local document retrieval for grounding agricultural recommendations.

Retrieval runs over a chunked text index (``corpus.jsonl``) produced from the
source PDF corpus by ``ingest.py``. It is fully local and deterministic: a
lexical BM25 score over the chunk text is combined with a tag-match boost
derived from the farm's evidence (crop, active hazards, irrigation type). No
embedding model, vector database, or network call is required, and PDFs are
never parsed at request time.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
CORPUS_PATH = KNOWLEDGE_DIR / "corpus.jsonl"

# BM25 parameters (standard defaults).
_BM25_K1 = 1.5
_BM25_B = 0.75

# Boost added to a passage's score for each kind of structured tag match.
# (Crop is a hard filter in ``retrieve``, so only hazard/irrigation are boosted.)
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
    text: str
    score: float
    tags: dict = field(default_factory=dict)


def _document_from_record(record: dict) -> Document:
    text = record.get("text", "")
    tokens = _tokenize(f"{record.get('source', '')} {text}")
    return Document(
        doc_id=record["doc_id"],
        title=record.get("title", record["doc_id"]),
        source=record.get("source", "unknown"),
        crop=str(record.get("crop", "")).lower(),
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


@dataclass(frozen=True)
class Query:
    terms: tuple[str, ...]
    crop: str
    irrigation: str
    hazards: frozenset[str]


def build_query(evidence: dict) -> Query:
    """Turn an evidence snapshot into a retrieval query."""
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

    text_parts = [
        crop,
        irrigation,
        " ".join(hazards),
        str(climate.get("climate_signal") or ""),
        str(forecast.get("forecast_signal") or ""),
        str(farm.get("farmer_notes") or ""),
    ]
    if "drought" in hazards:
        text_parts.append("water stress soil moisture irrigation rainfall mulch yield")
    if "flood" in hazards:
        text_parts.append("waterlogging drainage standing water submergence runoff")
    if "heat" in hazards:
        text_parts.append("high temperature heat stress tolerance flowering")

    return Query(
        terms=tuple(_tokenize(" ".join(part for part in text_parts if part))),
        crop=crop,
        irrigation=irrigation,
        hazards=frozenset(hazards),
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
    # Crop is applied as a hard filter in ``retrieve`` (the corpus is split by
    # crop), so the boost here only nudges ranking by hazard and irrigation.
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


def retrieve(evidence: dict, top_k: int = 4, max_per_source: int = 2) -> list[RetrievedPassage]:
    """Return the top-k guidance passages most relevant to the evidence.

    Candidates are restricted to documents for the farm's crop (when that crop
    exists in the corpus), and no more than ``max_per_source`` chunks are taken
    from any single source document so the grounding draws on several sources.
    """
    index = _load_index()
    if not index.documents:
        return []

    query = build_query(evidence)

    candidates = [d for d in index.documents if _matches_crop(query, d)]
    if not candidates:  # crop absent from corpus (e.g. sorghum) -> search everything
        candidates = list(index.documents)

    scored: list[RetrievedPassage] = []
    for document in candidates:
        lexical = _bm25_score(query.terms, document, index)
        if lexical <= 0:  # require some lexical relevance
            continue
        boost, matched = _tag_boost(query, document)
        scored.append(
            RetrievedPassage(
                doc_id=document.doc_id,
                title=document.title,
                source=document.source,
                crop=document.crop,
                text=document.text,
                score=round(lexical + boost, 4),
                tags={"matched": matched, "lexical": round(lexical, 4)},
            )
        )

    # Deterministic ordering: score desc, then doc_id for stable ties.
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
        {"doc_id": passage.doc_id, "title": passage.title, "source": passage.source}
        for passage in passages
    ]
