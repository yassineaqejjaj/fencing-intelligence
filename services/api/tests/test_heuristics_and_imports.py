from pathlib import Path

from fencing_domain.registry import doctor
from fencing_ml.datasets.fie_csv import import_fie_csv_tree
from fencing_ml.datasets.ffd import inspect_ffd
from fencing_ml.datasets.mfad import inspect_mfad
from fencing_ml.training.baseline import train_baseline
from ml_inference.movement import classify_track
from ml_inference.scoreboard import calibrated_distance_m, detect_light_candidates


def test_movement_heuristic_needs_direction_for_tactical_names():
    samples = [{"t_ms": index * 100, "position": index * 0.2, "low_stance": False} for index in range(8)]
    image_labels = {item["label"] for item in classify_track(samples)}
    assert "advance" not in image_labels
    directed = {item["label"] for item in classify_track(samples, forward="image_right")}
    assert "advance" in directed or "lunge" in directed or "fleche" in directed


def test_scoreboard_light_is_a_candidate_not_a_decision():
    dark = [[(10, 10, 10)]]
    red = [[(220, 20, 20)]]
    frames = [
        {"t_ms": 0, "pixels": dark},
        {"t_ms": 200, "pixels": red},
        {"t_ms": 400, "pixels": dark},
    ]
    found = detect_light_candidates(frames, {"x": 0, "y": 0, "w": 1, "h": 1})
    assert len(found) == 1
    assert found[0]["validated"] is False
    assert found[0]["referee_decision"] is None
    assert found[0]["score_value"] is None


def test_distance_without_calibration_stays_in_pixels():
    result = calibrated_distance_m({"x": 0, "y": 0}, {"x": 1, "y": 0}, None, 100, 50)
    assert result["unit"] == "pixels"
    assert result["meters"] is None


def test_fie_import_deduplicates_and_normalizes_weapon(tmp_path: Path):
    (tmp_path / "womens_foil_tournament_data.csv").write_text(
        "competition_ID,name,country,weapon,category,gender,season,start_date,end_date,url\n"
        "37,Memorial,SLOVAKIA,Foil,Junior,Womens,2015,2014-11-21,2014-11-22,https://fie.org/competitions/37\n"
    )
    (tmp_path / "womens_foil_fencer_bio_data.csv").write_text(
        "id,name,country,hand,age,date_accessed\n29240,Ada Example,FRA,Right,24,2020-01-01\n"
    )
    bout = (
        "fencer_ID,opp_ID,fencer_score,opp_score,winner_ID,tournament_ID,date,pool_ID,upset\n"
        "29240,27947,2,5,27947,37,2014-11-21,1,False\n"
        "29240,27947,2,5,27947,37,2014-11-21,1,False\n"
    )
    (tmp_path / "womens_foil_bout_data.csv").write_text(bout)
    parsed = import_fie_csv_tree(tmp_path)
    assert parsed["competitions"][0]["weapon"] == "foil"
    assert parsed["duplicate_bouts"] == 1
    assert len(parsed["bouts"]) == 1
    assert parsed["provenance"]["code_reused"] is False


def test_mfad_names_do_not_claim_rgb_footage(tmp_path: Path):
    skeleton = tmp_path / "skeleton"
    skeleton.mkdir()
    (skeleton / "1_p12_a1_1.npy").write_bytes(b"not-a-real-array")
    sensor = tmp_path / "sensor" / "1121"
    sensor.mkdir(parents=True)
    (sensor / "hand.txt").write_text("2022-08-19-14:50:53-322 0 0 0 0 0 1000\n")
    report = inspect_mfad(tmp_path)
    assert report["rgb_competition_footage"] is False
    assert report["labels"]["lunge"] == 1
    assert report["license"] == "unspecified"
    assert report["samples"][0]["level_name"] == "amateur"
    assert report["sensor_groups"][0]["segments"]["hand.txt"] == 1


def test_ffd_keeps_kinect_and_imu_apart(tmp_path: Path):
    (tmp_path / "SF_01_Body.mat").write_bytes(b"not-matlab")
    (tmp_path / "SF_01_IMU.mat").write_bytes(b"not-matlab")
    (tmp_path / "SF_01_Depth.avi").write_bytes(b"not-video")
    report = inspect_ffd(tmp_path)
    assert report["rgb_competition_footage"] is False
    assert report["sample_count"] == 1
    assert report["file_counts"]["imu"] == 1
    assert report["file_counts"]["kinect_depth"] == 1
    assert report["labels"]["step_forward"] == 1
    assert report["license"] == "unspecified"


def test_doctor_marks_missing_unlicensed_datasets(tmp_path: Path):
    report = doctor(tmp_path)
    by_name = {item["name"]: item for item in report["datasets"]}
    assert by_name["MFAD"]["presence"] == "missing"
    assert by_name["MFAD"]["compatibility"] == "incompatible"
    assert by_name["FIE-fencing-dataset"]["compatibility"] == "incompatible"
    assert report["counts"]["missing"] >= 4
    assert by_name["FI-synthetic-epee"]["presence"] == "installed"
    assert by_name["FI-synthetic-epee"]["license"] == "Apache-2.0"


def test_pose_landmarker_does_not_name_actions():
    pytest = __import__("pytest")
    np = pytest.importorskip("numpy")
    pytest.importorskip("mediapipe")
    from ml_inference.pose import estimate_rgb

    blank = np.zeros((96, 96, 3), dtype="uint8")
    result = estimate_rgb(blank)
    assert result["claim_accuracy"] is False
    assert result["tactical_labels"] is False
    assert result["poses"] == []


def test_baseline_refuses_without_a_license_acknowledgement():
    try:
        train_baseline([[0, 0], [1, 1]], ["a", "b"], acknowledge_license=False)
    except RuntimeError as exc:
        assert "Refusing" in str(exc)
    else:
        raise AssertionError("training should have been refused")


def test_synthetic_baseline_is_not_a_fencing_claim():
    pytest = __import__("pytest")
    try:
        import numpy  # noqa: F401
        import sklearn  # noqa: F401
    except ImportError:
        pytest.skip("scientific stack is not installed")
    rows = [[0.1, 0.2]] * 8 + [[2.0, 3.0]] * 8
    labels = ["hold"] * 8 + ["lunge"] * 8
    result = train_baseline(rows, labels, acknowledge_license=False, synthetic=True)
    assert result["claim_accuracy"] is False
    assert result["synthetic"] is True
    assert result["status"] == "experimental"
