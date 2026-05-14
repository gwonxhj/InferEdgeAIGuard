from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_readme_exposes_detector_verdict_matrix():
    readme = _read("README.md")

    assert "Detector Verdict Matrix" in readme
    assert "AIGuard detectors are deterministic evidence providers" in readme
    assert "InferEdgeLab remains the final" in readme
    assert "detection disappearance" in readme
    assert "calibration drift" in readme


def test_detector_matrix_documents_current_and_next_detectors():
    matrix = _read("docs/detector_validation_matrix.md")

    for required in [
        "bbox validity",
        "bbox collapse",
        "confidence saturation",
        "detection disappearance",
        "baseline deviation",
        "temporal consistency",
        "provenance consistency",
        "per-class detection drift",
        "calibration drift",
        "baseline profile stability",
    ]:
        assert required in matrix

    assert "not the final Lab deployment policy" in matrix
    assert "not LLM" in matrix
