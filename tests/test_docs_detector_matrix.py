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
    assert "Baseline profile stability metadata" in readme


def test_readmes_expose_optional_aiguard_role_boundaries():
    readme = _read("README.md")
    readme_ko = _read("README.ko.md")

    assert "Language: English | [한국어](README.ko.md)" in readme
    assert "언어: [English](README.md) | 한국어" in readme_ko

    for required in [
        "## Role Boundary At A Glance",
        "Replace or overwrite InferEdgeLab `deployment_decision`",
        "Recompute comparability, own the registry, or decide deployment",
        "production remote execution proof",
        "LLM-based root-cause certainty",
        "automatic remediation",
    ]:
        assert required in readme

    for required in [
        "## 역할 경계 한눈에 보기",
        "InferEdgeLab의 `deployment_decision`을 대체하거나 덮어쓰지 않습니다.",
        "comparability를 재계산하거나 registry를 소유하거나 deployment를 결정하지 않습니다.",
        "production remote execution proof가 되지 않습니다.",
        "LLM 기반 root-cause 확정",
        "automatic remediation",
    ]:
        assert required in readme_ko


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
        "profile_stability",
    ]:
        assert required in matrix

    assert "not the final Lab deployment policy" in matrix
    assert "not LLM" in matrix


def test_detector_matrix_bounds_calibration_drift_evidence_policy():
    readme = _read("README.md")
    readme_ko = _read("README.ko.md")
    matrix = _read("docs/detector_validation_matrix.md")
    matrix_ko = _read("docs/detector_validation_matrix.ko.md")

    for required in [
        "## Calibration Drift Evidence Policy",
        "implemented as additive baseline-comparison evidence",
        "known-good baseline profile",
        "fixed-bin score histogram distance",
        "histogram distance `>= 0.30`",
        "mean_score_delta",
        "absolute mean score delta `>= 0.20`",
        "std_score_delta",
        "score std drops below `0.05`",
        "saturation delta `>= 0.30`",
        "evidence[].type=calibration_drift",
        "does not change the diagnosis report schema",
        "not automatic root-cause proof",
        "Do not make AIGuard a Lab `deployment_decision` owner.",
    ]:
        assert required in matrix

    for required in [
        "Calibration drift evidence policy",
        "additive baseline-comparison evidence",
        "known-good baseline profile",
        "histogram distance `>= 0.30`",
        "absolute mean score delta `>= 0.20`",
        "candidate std `< 0.05`",
        "saturation delta `>= 0.30`",
        "`evidence[].type=calibration_drift`",
        "Lab `deployment_decision`",
        "Runtime result contract",
    ]:
        assert required in matrix_ko

    assert "Calibration drift (`calibration_drift`) is" in readme
    assert "`calibration_drift`가 포함됩니다" in readme_ko


def test_detector_matrix_documents_baseline_profile_stability_metadata():
    readme = _read("README.md")
    readme_ko = _read("README.ko.md")
    matrix = _read("docs/detector_validation_matrix.md")
    matrix_ko = _read("docs/detector_validation_matrix.ko.md")

    for required in [
        "## Baseline Profile Stability Metadata",
        "Saved baseline profiles include additive `profile_stability`",
        "`profile_stability.sample_count`",
        "`profile_stability.min_sample_count_review`",
        "`profile_stability.score_histogram_total_scores`",
        "`profile_stability.class_distribution_total_predictions`",
        "`profile_stability.compatibility_status`",
        "legacy_profile_missing_profile_stability",
        "does not change the diagnosis report schema",
    ]:
        assert required in matrix

    for required in [
        "Baseline profile stability metadata",
        "`profile_stability` audit metadata",
        "`profile_stability.sample_count`",
        "`profile_stability.compatibility_status`",
        "legacy_profile_missing_profile_stability",
        "schema는 변경하지 않습니다",
    ]:
        assert required in matrix_ko

    assert "Baseline profile stability metadata (`profile_stability`)" in readme
    assert "`profile_stability` audit metadata" in readme_ko


def test_detector_matrix_has_korean_quick_guide_and_boundaries():
    readme = _read("README.md")
    readme_ko = _read("README.ko.md")
    matrix = _read("docs/detector_validation_matrix.md")
    matrix_ko = _read("docs/detector_validation_matrix.ko.md")

    assert "Language: English | [한국어](detector_validation_matrix.ko.md)" in matrix
    assert "언어: [English](detector_validation_matrix.md) | 한국어" in matrix_ko
    assert "[Detector Validation Matrix](detector_validation_matrix.md)" in matrix_ko
    assert "대표/canonical 문서" in matrix_ko
    assert (
        "[docs/detector_validation_matrix.md]"
        "(docs/detector_validation_matrix.md)"
        in readme
    )
    assert (
        "[한국어: detector validation matrix quick guide]"
        "(docs/detector_validation_matrix.ko.md)"
        in readme
    )
    assert (
        "[Detector Validation Matrix](docs/detector_validation_matrix.ko.md)"
        in readme_ko
    )
    assert "[English matrix](docs/detector_validation_matrix.md)" in readme_ko

    for required in [
        "`guard_verdict`",
        "`deployment_decision`",
        "InferEdgeLab",
        "Lab-owned deployment decision",
        "LLM-based root-cause certainty",
        "automatic remediation",
        "EdgeEnv comparability",
        "runtime regression",
        "production remote execution proof",
        "production observability platform",
        "general monitoring SaaS",
        "public leaderboard",
        "Jetson 필요 여부",
    ]:
        assert required in matrix_ko
