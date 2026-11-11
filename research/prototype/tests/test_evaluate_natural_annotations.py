import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_natural_annotations.py"
SPEC = importlib.util.spec_from_file_location("evaluate_natural_annotations", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_metrics_confusion_and_macro_f1():
    rows = [("d1", "ENTAILED", "ENTAILED"),
            ("d1", "CONTRADICTED", "NOT_ENOUGH_INFORMATION"),
            ("d2", "NOT_ENOUGH_INFORMATION", "NOT_ENOUGH_INFORMATION")]
    result = MOD.metrics(rows)
    assert result["n"] == 3
    assert result["accuracy"] == 2 / 3
    assert result["confusion_matrix_gold_rows_predicted_columns"]["CONTRADICTED"]["NOT_ENOUGH_INFORMATION"] == 1


def test_no_evidence_is_coverage_not_automatically_nei():
    annotations = {
        ("d1", "c1"): {"adjudicated_label": "CONTRADICTED"},
        ("d2", "c1"): {"adjudicated_label": "NOT_ENOUGH_INFORMATION"},
    }
    predictions = {("d1", "c1"): "NO_EVIDENCE",
                   ("d2", "c1"): "NOT_ENOUGH_INFORMATION"}
    result = MOD.evaluate(annotations, predictions, bootstrap=100, seed=3)
    assert result["n_no_evidence"] == 1
    assert result["n_prediction_labelled"] == 1
    assert result["evidence_coverage_on_annotated_claims"] == 0.5
    assert result["selective_metrics_on_evidence_labelled_subset"]["accuracy"] == 1.0


def test_case_cluster_bootstrap_is_reproducible():
    annotations = {("a", "1"): {"adjudicated_label": "ENTAILED"},
                   ("b", "1"): {"adjudicated_label": "CONTRADICTED"}}
    predictions = {("a", "1"): "ENTAILED", ("b", "1"): "CONTRADICTED"}
    x = MOD.evaluate(annotations, predictions, 100, 42)
    y = MOD.evaluate(annotations, predictions, 100, 42)
    assert x["cluster_bootstrap"] == y["cluster_bootstrap"]
