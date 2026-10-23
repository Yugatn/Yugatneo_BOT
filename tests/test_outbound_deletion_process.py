"""Cross-process check: deletion marker survives worker restart."""
import subprocess
import sys

from app.services.personal_data import delete_telegram_user_records


def test_deletion_fence_survives_new_python_process(tmp_path):
    db_path = tmp_path / "two-process.sqlite"
    delete_telegram_user_records(db_path, "synthetic-17")
    script = (
        "import sys;"
        "from app.services.outbound_delivery import reserve_user_delivery;"
        "assert reserve_user_delivery(sys.argv[1], 'synthetic-17', 'late-event') is False;"
        "assert reserve_user_delivery(sys.argv[1], 'synthetic-18', 'other-event') is True"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(db_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
