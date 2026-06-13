from app.modules.knowledge.chunking import chunk_text, infer_metadata
from app.modules.knowledge.drive_client import normalize_drive_folder_id
from app.modules.knowledge.retrieval import build_retrieval_query, tokenize


def test_chunk_text_splits_long_guidance() -> None:
    text = " ".join(f"word{i}" for i in range(1000))

    chunks = chunk_text(text, max_words=200, overlap_words=30)

    assert len(chunks) > 1
    assert "word0" in chunks[0]
    assert "word999" in chunks[-1]


def test_infer_metadata_detects_crop_and_topic() -> None:
    metadata = infer_metadata(
        "Maize drought guide.pdf",
        "Use mulch to reduce moisture loss during drought and dry spells.",
    )

    assert metadata["crop"] == "maize"
    assert metadata["topic"] == "drought"


def test_retrieval_query_uses_farmer_notes_and_risk_drivers() -> None:
    query = build_retrieval_query(
        {
            "farm": {
                "crop": "maize",
                "irrigation_type": "rainfed",
                "farmer_notes": "Upper slope dries quickly.",
            },
            "climate": {"climate_signal": "drier than usual"},
            "vegetation": {"water_stress": "high"},
            "risk": {
                "overall_risk_level": "high",
                "drought_level": "high",
                "drought_drivers": ["Rainfall is below historical average"],
            },
        }
    )

    tokens = tokenize(query)

    assert "maize" in tokens
    assert "rainfed" in tokens
    assert "drought" in tokens
    assert "rainfall" in tokens


def test_normalize_drive_folder_id_accepts_full_folder_url() -> None:
    folder_id = normalize_drive_folder_id(
        "https://drive.google.com/drive/folders/1EQ3RzGVC7W591Wr9FL4fcQWV9zx7qV99"
    )

    assert folder_id == "1EQ3RzGVC7W591Wr9FL4fcQWV9zx7qV99"
