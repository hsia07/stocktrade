"""
Tests that stocktrade/ stale copy manual start .bat files are fail-closed.
All three bat files (start.bat, run.bat, 啟動-server.bat) must:
  - Print a deprecation/archived message
  - Exit with error code (not launch server_v2.py)
  - Not contain python server_v2.py, uvicorn, or any server start command
"""

import os
import subprocess
import pytest

SUBMOUDLE_DIR = os.path.join(os.path.dirname(__file__), "..", "stocktrade")

BAT_FILES = {
    "start.bat": os.path.join(SUBMOUDLE_DIR, "start.bat"),
    "run.bat": os.path.join(SUBMOUDLE_DIR, "run.bat"),
    "啟動-server.bat": os.path.join(SUBMOUDLE_DIR, "啟動-server.bat"),
}

FORBIDDEN_PATTERNS = [
    "python server_v2.py",
    "uvicorn",
    "start server",
    "shioaji",
    "fubon",
]


class TestStaleCopyManualStartersFailClosed:
    def test_all_bat_files_exist(self):
        for name, path in BAT_FILES.items():
            assert os.path.exists(path), f"{name} not found at {path}"

    def test_start_bat_fail_closed(self):
        path = BAT_FILES["start.bat"]
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "DEPRECATED" in content or "deprecated" in content, \
            "start.bat must show deprecation message"
        assert "exit /b 1" in content, "start.bat must exit with error"
        assert "python server_v2.py" not in content, \
            "start.bat must not launch server_v2.py"

    def test_run_bat_fail_closed(self):
        path = BAT_FILES["run.bat"]
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "DEPRECATED" in content or "deprecated" in content or "archived" in content, \
            "run.bat must show deprecation/archived message"
        assert "exit /b 1" in content, "run.bat must exit with error"
        assert "python server_v2.py" not in content, \
            "run.bat must not launch server_v2.py"

    def test_tw_start_server_bat_fail_closed(self):
        path = BAT_FILES["啟動-server.bat"]
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "DEPRECATED" in content or "deprecated" in content or "archived" in content, \
            "啟動-server.bat must show deprecation/archived message"
        assert "exit /b 1" in content, "啟動-server.bat must exit with error"
        assert "python server_v2.py" not in content, \
            "啟動-server.bat must not launch server_v2.py"

    def test_no_bat_contains_forbidden_patterns(self):
        for name, path in BAT_FILES.items():
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in content:
                    pytest.fail(f"{name} contains forbidden pattern: {pattern}")

    def test_start_bat_exits_with_error(self):
        import subprocess
        result = subprocess.run(
            [BAT_FILES["start.bat"]],
            shell=True,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "start.bat must exit with non-zero"

    def test_run_bat_exits_with_error(self):
        import subprocess
        result = subprocess.run(
            [BAT_FILES["run.bat"]],
            shell=True,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "run.bat must exit with non-zero"

    def test_tw_start_server_bat_exits_with_error(self):
        import subprocess
        result = subprocess.run(
            [BAT_FILES["啟動-server.bat"]],
            shell=True,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "啟動-server.bat must exit with non-zero"

    def test_stale_index_v2_archived(self):
        index_path = os.path.join(SUBMOUDLE_DIR, "index_v2.html")
        assert os.path.exists(index_path), "stale index_v2.html must exist"
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        FORBIDDEN_UI = [
            "modebtn2", "forceCloseCommand", "undefined",
            "R049", "R030", "broker_live", "trading_controls",
        ]
        for pat in FORBIDDEN_UI:
            assert pat not in content, f"stale index_v2.html must not contain: {pat}"
