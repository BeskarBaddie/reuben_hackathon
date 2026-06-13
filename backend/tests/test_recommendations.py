from datetime import date
from uuid import uuid4

from app.modules.analysis.models import FarmAnalysis
from app.modules.analysis.schemas import AnalysisStatus
from app.modules.farms.models import Farm, IrrigationType
from app.modules.recommendations.forecast import build_forecast
from app.modules.recommendations.retrieval import (
    build_query,
    citations_from_passages,
    is_crop_supported,
    retrieve,
)
from app.modules.recommendations.schemas import RecommendationOutput
from app.modules.recommendations.service import (
    build_evidence_snapshot,
    generate_deterministic_recommendations,
)


def _high_drought_farm_and_analysis() -> tuple[Farm, FarmAnalysis]:
    farm = Farm(
        id=uuid4(),
        owner_id=uuid4(),
        name="Field A",
        crop="maize",
        planting_date=date(2026, 5, 1),
        irrigation_type=IrrigationType.RAINFED,
        area_hectares=2.4,
        boundary="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
        notes="Farmer says the top end of the field dries first and water access is limited.",
    )
    analysis = FarmAnalysis(
        id=uuid4(),
        farm_id=farm.id,
        status=AnalysisStatus.COMPLETED,
        ndvi=0.1,
        vegetation_health="stressed",
        water_stress="high",
        rainfall_this_season_mm=177.0,
        rainfall_historical_average_mm=300.0,
        rainfall_anomaly_percent=-41,
        temperature_anomaly_c=0.4,
        climate_signal="drier than usual",
        drought_score=100,
        drought_level="high",
        drought_drivers=[
            "Rainfall is 41% below historical average",
            "NDVI indicates severe vegetation stress",
        ],
        flood_score=0,
        flood_level="low",
        heat_score=17,
        heat_level="low",
        overall_risk_level="high",
    )
    return farm, analysis


def test_deterministic_recommendations_prioritize_high_drought() -> None:
    farm, analysis = _high_drought_farm_and_analysis()

    output = generate_deterministic_recommendations(build_evidence_snapshot(farm, analysis))

    assert output["actions"][0]["priority"] == 1
    assert "Mulch" in output["actions"][0]["action"]
    assert output["actions"][0]["evidence"]


def test_deterministic_output_includes_prose_and_forecast() -> None:
    farm, analysis = _high_drought_farm_and_analysis()
    evidence = build_evidence_snapshot(farm, analysis)

    passages = retrieve(evidence)
    output = generate_deterministic_recommendations(evidence, passages)
    output["citations"] = citations_from_passages(passages)

    # Prose narrative is non-trivial and ties to the crop and a forecast statement.
    assert len(output["narrative"].split()) >= 20
    assert "maize" in output["narrative"]
    assert output["forecast_summary"]

    # Citations are real documents that were actually retrieved.
    assert output["citations"]
    retrieved_ids = {passage.doc_id for passage in passages}
    assert all(citation["doc_id"] in retrieved_ids for citation in output["citations"])

    # The full output validates against the response schema.
    RecommendationOutput.model_validate(output)


def test_evidence_snapshot_includes_farmer_notes_and_forecast() -> None:
    farm = Farm(
        id=uuid4(),
        owner_id=uuid4(),
        name="Field B",
        crop="maize",
        planting_date=date(2026, 5, 1),
        expected_harvest_date=date(2026, 9, 1),
        irrigation_type=IrrigationType.PARTIAL,
        area_hectares=1.8,
        boundary="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
        notes="Low area floods after heavy rain; upper slope is sandy.",
    )
    analysis = FarmAnalysis(
        id=uuid4(),
        farm_id=farm.id,
        status=AnalysisStatus.COMPLETED,
        overall_risk_level="medium",
    )

    evidence = build_evidence_snapshot(farm, analysis)

    assert evidence["farm"]["farmer_notes"] == "Low area floods after heavy rain; upper slope is sandy."
    assert evidence["farm"]["expected_harvest_date"] == "2026-09-01"
    assert "forecast" in evidence
    assert evidence["forecast"]["horizon_days"] >= 1
    assert "forecast_signal" in evidence["forecast"]


def test_retrieval_selects_crop_relevant_documents() -> None:
    evidence = {
        "farm": {"crop": "maize", "irrigation_type": "partial"},
        "risk": {"drought_level": "high", "flood_level": "low", "heat_level": "low"},
        "vegetation": {"water_stress": "high"},
        "climate": {"climate_signal": "drier than usual"},
    }

    query = build_query(evidence)
    assert "drought" in query.hazards

    passages = retrieve(evidence)

    # The ingested PDF corpus is populated and a maize query surfaces maize
    # documents, not rice documents.
    assert passages
    crops = {passage.crop for passage in passages}
    assert "maize" in crops
    assert "rice" not in crops


def test_mock_forecast_continues_dry_season_trend() -> None:
    farm, analysis = _high_drought_farm_and_analysis()
    climate = build_evidence_snapshot(farm, analysis)["climate"]

    forecast = build_forecast(farm, climate)

    # A dry season (rainfall well below normal) carries a drier-than-normal outlook
    # forward (the short-term forecast regresses part-way back toward normal, so it is
    # negative but milder than the full-season anomaly).
    assert forecast["rainfall_outlook_percent"] < 0
    assert forecast["forecast_signal"] != "wetter than normal"
    assert forecast["forecast_signal"] in {
        "drier than normal",
        "hot and dry",
        "near normal",
    }


def test_unsupported_crop_retrieves_nothing() -> None:
    # The corpus covers maize and rice; wheat is not present.
    assert is_crop_supported("maize") is True
    assert is_crop_supported("wheat") is False

    evidence = {
        "farm": {"crop": "wheat", "irrigation_type": "rainfed"},
        "risk": {"drought_level": "high", "flood_level": "low", "heat_level": "low"},
        "vegetation": {"water_stress": "high"},
        "climate": {"climate_signal": "drier than usual"},
    }

    # No documents for wheat -> retrieval returns nothing, rather than falling
    # back to maize/rice documents.
    assert retrieve(evidence) == []


def test_unsupported_crop_output_flags_insufficient_data() -> None:
    farm = Farm(
        id=uuid4(),
        owner_id=uuid4(),
        name="Wheat Field",
        crop="wheat",
        irrigation_type=IrrigationType.RAINFED,
        area_hectares=3.0,
        boundary="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
    )
    analysis = FarmAnalysis(
        id=uuid4(),
        farm_id=farm.id,
        status=AnalysisStatus.COMPLETED,
        drought_level="high",
        flood_level="low",
        heat_level="low",
        overall_risk_level="high",
        drought_drivers=["Rainfall well below average"],
    )
    evidence = build_evidence_snapshot(farm, analysis)
    passages = retrieve(evidence)

    output = generate_deterministic_recommendations(evidence, passages, crop_supported=False)

    # The summary and narrative must clearly state the crop is unsupported and
    # name the crops that are covered.
    assert "wheat" in output["summary"].lower()
    assert "not enough" in output["summary"].lower() or "insufficient" in output["summary"].lower()
    assert "maize" in output["summary"].lower() and "rice" in output["summary"].lower()
    assert "not specific to wheat" in output["narrative"].lower()

    # No fabricated citations for an unsupported crop.
    assert citations_from_passages(passages) == []


def test_action_grounding_flags_supported_and_unsupported(monkeypatch) -> None:
    import numpy as np

    from app.modules.recommendations import service as svc
    from app.modules.recommendations.retrieval import RetrievedPassage

    supported_vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    unrelated_vec = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    passages = [
        RetrievedPassage(
            doc_id="maize_guide__0005",
            title="Maize guide (p. 5)",
            source="Maize guide",
            crop="maize",
            path="Maize/maize_guide.pdf",
            page=5,
            text="Mulch conserves soil moisture in the root zone.",
            score=0.9,
            vector=supported_vec,
        )
    ]

    def fake_embed_text(text: str, timeout: float = 60.0):
        return supported_vec if "mulch" in text.lower() else unrelated_vec

    monkeypatch.setattr(svc, "embed_text", fake_embed_text)

    output = {
        "actions": [
            {"action": "Apply mulch around the plants", "reason": "retain soil moisture", "evidence": ["x"]},
            {"action": "Build a perimeter fence", "reason": "keep livestock out", "evidence": ["y"]},
        ]
    }
    svc.attach_action_grounding(output, passages)

    grounded = output["actions"][0]["grounding"]
    ungrounded = output["actions"][1]["grounding"]
    assert grounded["grounded"] is True
    assert grounded["source"] == "Maize guide"
    assert grounded["path"] == "Maize/maize_guide.pdf"
    assert grounded["page"] == 5
    assert ungrounded["grounded"] is False


def test_action_grounding_skipped_without_passages() -> None:
    from app.modules.recommendations import service as svc

    output = {"actions": [{"action": "Do a thing", "reason": "because", "evidence": ["z"]}]}
    svc.attach_action_grounding(output, [])
    assert "grounding" not in output["actions"][0]
