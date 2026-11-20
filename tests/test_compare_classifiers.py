import numpy as np
import pytest

from scripts.compare_classifiers import compare, synthetic_features, verify_partition


def test_compare_reports_both_training_conditions_with_one_validation_set():
    train, validation, historical = synthetic_features()
    result = compare(train, validation, historical)
    assert result["validation_samples"] == 48
    assert result["conditions"]["new_train"]["train_samples"] == 48
    assert result["conditions"]["new_train_plus_s01"]["train_samples"] == 96
    for condition in result["conditions"].values():
        models = condition["classifiers"]
        assert set(models) == {"SVM", "Random Forest", "k-NN", "MLP"}
        for model in models.values():
            assert np.asarray(model["validation_confusion_rows_actual"]).shape == (4, 4)
            assert np.sum(model["validation_confusion_rows_actual"]) == 48


def test_compare_rejects_session_and_vector_leakage():
    train, validation, historical = synthetic_features()
    with pytest.raises(ValueError, match="comparten una sesión"):
        compare(train, train)
    validation["vectors"][0] = train["vectors"][0]
    with pytest.raises(ValueError, match="vectores idénticos"):
        compare(train, validation)
    with pytest.raises(ValueError, match="no coincide"):
        compare(historical, validation)


def test_partition_guard_refuses_test_samples():
    train, _, _ = synthetic_features()
    schedule = {f"K0{number}_S02": {"split": "TEST"} for number in range(1, 5)}
    with pytest.raises(ValueError, match="no pertenece a TRAIN"):
        verify_partition(train, schedule, "TRAIN")
