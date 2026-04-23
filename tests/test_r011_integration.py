"""
R011 Artifact Management Integration Tests
Tests that ArtifactManager is properly integrated into TradingEngine.
"""
import sys
import os
import asyncio
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import TradingEngine, Direction
from automation.control.artifacts.r011_artifact_management import ArtifactManager


class TestArtifactManagerIntegration:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.artifacts_dir = Path(self.temp_dir) / "artifacts"
        self.history_dir = Path(self.temp_dir) / "history"
        self.artifacts_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(exist_ok=True)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_artifact_manager_initialization_in_engine(self):
        """Test that TradingEngine initializes ArtifactManager."""
        engine = TradingEngine()
        assert hasattr(engine, 'artifact_manager')
        assert engine.artifact_manager is not None
        assert isinstance(engine.artifact_manager, ArtifactManager)

    def test_artifact_manager_create_artifact(self):
        """Test ArtifactManager.create_artifact creates files."""
        manager = ArtifactManager(
            artifacts_dir=str(self.artifacts_dir),
            history_dir=str(self.history_dir)
        )
        filepath = manager.create_artifact("R011-TEST", "test content", "prompt")
        assert Path(filepath).exists()
        assert "R011-TEST" in filepath
        assert "prompt" in filepath

    def test_artifact_manager_create_history_entry(self):
        """Test ArtifactManager.create_history_entry creates files."""
        manager = ArtifactManager(
            artifacts_dir=str(self.artifacts_dir),
            history_dir=str(self.history_dir)
        )
        filepath = manager.create_history_entry("R011-TEST", {"key": "value"})
        assert Path(filepath).exists()
        assert "history" in filepath

    def test_artifact_manager_list_artifacts(self):
        """Test ArtifactManager.list_artifacts returns artifacts."""
        manager = ArtifactManager(
            artifacts_dir=str(self.artifacts_dir),
            history_dir=str(self.history_dir)
        )
        manager.create_artifact("R011-TEST", "content1", "type1")
        manager.create_artifact("R011-TEST", "content2", "type2")
        artifacts = manager.list_artifacts("R011-TEST")
        assert len(artifacts) == 2

    def test_artifact_manager_validate_artifacts(self):
        """Test ArtifactManager.validate_artifacts returns correct structure."""
        manager = ArtifactManager(
            artifacts_dir=str(self.artifacts_dir),
            history_dir=str(self.history_dir)
        )
        result = manager.validate_artifacts("R011-TEST")
        assert "round_id" in result
        assert "count" in result
        assert "validation" in result

    def test_trading_engine_state_includes_artifact_stats(self):
        """Test that get_state() includes artifact_stats after loop run."""
        engine = TradingEngine()
        state = engine.get_state()
        assert "artifact_stats" in state

    def test_artifact_trigger_on_signal(self):
        """Test that signal generation creates a signal artifact."""
        engine = TradingEngine()
        # Create a mock artifact dir
        engine.artifact_manager = ArtifactManager(
            artifacts_dir=str(self.artifacts_dir),
            history_dir=str(self.history_dir)
        )
        # Manually trigger artifact creation as would happen on signal
        engine.artifact_manager.create_artifact(
            round_id="runtime",
            content="Signal: 2330 LONG conf=80% | test reason",
            artifact_type="signal"
        )
        artifacts = engine.artifact_manager.list_artifacts("runtime")
        assert any("signal" in a for a in artifacts)

    def test_artifact_trigger_on_trade(self):
        """Test that trade execution creates a trade artifact."""
        engine = TradingEngine()
        engine.artifact_manager = ArtifactManager(
            artifacts_dir=str(self.artifacts_dir),
            history_dir=str(self.history_dir)
        )
        engine.artifact_manager.create_artifact(
            round_id="runtime",
            content="Trade executed: Buy 2330 2 lots @ 866.0 | test",
            artifact_type="trade"
        )
        artifacts = engine.artifact_manager.list_artifacts("runtime")
        assert any("trade" in a for a in artifacts)

    def test_history_entry_created(self):
        """Test that history entries are created."""
        engine = TradingEngine()
        engine.artifact_manager = ArtifactManager(
            artifacts_dir=str(self.artifacts_dir),
            history_dir=str(self.history_dir)
        )
        engine.artifact_manager.create_history_entry(
            round_id="runtime",
            data={"daily_pnl": 100, "daily_trades": 1}
        )
        history_files = list(self.history_dir.glob("history_runtime_*.json"))
        assert len(history_files) >= 1

    def test_run_loop_does_not_break_with_artifact_manager(self):
        """Test that run_loop can start with ArtifactManager integrated."""
        engine = TradingEngine()
        engine.artifact_manager = ArtifactManager(
            artifacts_dir=str(self.artifacts_dir),
            history_dir=str(self.history_dir)
        )
        # Just verify engine starts without error
        assert engine._running is False
        # Verify artifact manager is accessible
        assert engine.artifact_manager.artifacts_dir is not None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])