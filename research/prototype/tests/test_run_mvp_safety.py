"""CLI safety tests: atomic output and preflight case-count validation."""
import json
from argparse import Namespace

from scripts.run_mvp import _write_records_atomically, cmd_run


def test_atomic_writer_replaces_output_with_complete_jsonl(tmp_path):
    output = tmp_path / "run.jsonl"
    output.write_text("old result\n", encoding="utf-8")

    _write_records_atomically(output, [{"id": 1}, {"id": 2}])

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert rows == [{"id": 1}, {"id": 2}]
    assert list(tmp_path.glob(".run.jsonl.*.tmp")) == []


def test_atomic_writer_preserves_previous_output_on_generation_failure(tmp_path):
    output = tmp_path / "run.jsonl"
    output.write_text("previous successful result\n", encoding="utf-8")

    def interrupted_records():
        yield {"id": 1}
        raise RuntimeError("simulated model failure")

    try:
        _write_records_atomically(output, interrupted_records())
    except RuntimeError as exc:
        assert "simulated model failure" in str(exc)
    else:
        raise AssertionError("expected the simulated run failure")

    assert output.read_text(encoding="utf-8") == "previous successful result\n"
    assert list(tmp_path.glob(".run.jsonl.*.tmp")) == []


def test_cli_rejects_zero_and_negative_case_counts_before_model_loading(capsys):
    for count in (0, -1):
        assert cmd_run(Namespace(num_cases=count)) == 1
        assert "--num-cases must be between 1 and 5" in capsys.readouterr().out
