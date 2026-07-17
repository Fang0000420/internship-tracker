import pytest

from internship_tracker.cli import main


def test_main_prints_ready_message(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    captured = capsys.readouterr()
    assert captured.out == "internship-tracker is ready!\n"
    assert captured.err == ""
