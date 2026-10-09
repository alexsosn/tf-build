from pathlib import Path


def test_ci_cancels_superseded_runs_per_ref() -> None:
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    lines = workflow.splitlines()

    index = lines.index("concurrency:")
    assert lines[index + 1] == "  group: ${{ github.workflow }}-${{ github.ref }}"
    assert lines[index + 2] == "  cancel-in-progress: true"
