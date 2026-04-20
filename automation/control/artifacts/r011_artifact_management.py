"""
Artifact Management System for R-011
Provides structured artifact tracking and history management
"""
import json
import os
from datetime import datetime
from pathlib import Path


class ArtifactManager:
    def __init__(self, artifacts_dir: str, history_dir: str = None):
        self.artifacts_dir = Path(artifacts_dir)
        self.history_dir = Path(history_dir) if history_dir else self.artifacts_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def create_artifact(self, round_id: str, content: str, artifact_type: str = "prompt") -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{artifact_type}_{round_id}_{timestamp}.txt"
        filepath = self.artifacts_dir / filename
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def create_history_entry(self, round_id: str, data: dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"history_{round_id}_{timestamp}.json"
        filepath = self.history_dir / filename
        entry = {
            "round_id": round_id,
            "timestamp": timestamp,
            "data": data
        }
        filepath.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(filepath)

    def get_latest_artifact(self, round_id: str = None) -> str:
        artifacts = sorted(self.artifacts_dir.glob(f"*{round_id if round_id else '*'}_*.txt"),
                         key=lambda p: p.stat().st_mtime, reverse=True)
        return str(artifacts[0]) if artifacts else None

    def list_artifacts(self, round_id: str = None) -> list:
        pattern = f"*{round_id if round_id else '*'}_*.txt"
        return [str(p) for p in sorted(self.artifacts_dir.glob(pattern),
                                 key=lambda p: p.stat().st_mtime, reverse=True)]

    def validate_artifacts(self, round_id: str) -> dict:
        artifacts = self.list_artifacts(round_id)
        return {
            "round_id": round_id,
            "count": len(artifacts),
            "artifacts": artifacts,
            "validation": "PASS" if artifacts else "EMPTY"
        }


if __name__ == "__main__":
    manager = ArtifactManager(
        artifacts_dir="automation/control/artifacts",
        history_dir="automation/control/history"
    )
    result = manager.validate_artifacts("R-011")
    print(json.dumps(result, indent=2, ensure_ascii=False))