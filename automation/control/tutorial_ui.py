"""
PHASE2-API-AUTOMODE-R022: 新手可理解化 / 教學式 UI - Complete Implementation
With: Newcomer/Advanced mode, Plain language, Signal lights, Tutorial page
Renders from unified truth source (current_round.yaml / AUTO_MODE_ACTIVATION_LOCK)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger("tutorial_ui")


class UserMode(str, Enum):
    NEWCOMER = "newcomer"
    ADVANCED = "advanced"


class SignalStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class TutorialUI:
    """
    Complete Tutorial UI for R022: 新手可理解化 / 教學式 UI
    
    Mandatory items:
    1. NewcomerMode / AdvancedMode - mode switching
    2. Plain language explanation layer
    3. Signal/light status system
    4. Tutorial page / onboarding flow
    5. Unified truth source rendering (same as backend)
    """

    DEFAULT_TERMS = {
        "當日沖銷": {
            "newcomer": "就是今天買的股票，今天賣掉。不留到明天。",
            "advanced": "Day trade: 同一天內完成買入和賣出，根據 T+0 規則。"
        },
        "停損": {
            "newcomer": "虧錢到了一定金額，就自動賣掉，防止繼續虧。",
            "advanced": "Stop loss: 當虧損達到設定上限時強制平倉的風險控制機制。"
        },
        "停利": {
            "newcomer": "賺錢到了一定金額，就先落袋為安。",
            "advanced": "Take profit: 當獲利達到設定目標時自動平倉的獲利保護機制。"
        },
        "六大會議": {
            "newcomer": "AI 每天分析市場的六個步驟，幫你決定要不要買賣。",
            "advanced": "AI Decision Conferences: 晨間/新聞/風險/選股/買賣/複盤六階段分析。"
        },
        "部位": {
            "newcomer": "你現在持有哪些股票。",
            "advanced": "Position: 投資組合中持有的股票及其數量。"
        },
        "選股池": {
            "newcomer": "AI 推薦可以看看的股票清單。",
            "advanced": "Watchlist: AI 根據策略篩選出的候選股票清單。"
        }
    }

    TUTORIAL_STEPS = [
        {
            "step_id": "step_1",
            "title": "歡迎使用當沖機器人",
            "title_newcomer": "歡迎使用 AI 幫你炒股",
            "description": "本研究平台提供 AI 輔助交易決策，請先了解基本操作流程。",
            "description_newcomer": "這個系統會幫你分析市場、建議股票，但最終決定還是要你來做。",
            "key_points": ["AI 提供建議而非直接交易", "最終交易決定權在您", "請先閱讀風險說明"],
            "key_points_newcomer": ["AI 是幫手，不是老闆", "賺錢虧錢都是你的", "要先學怎麼用"]
        },
        {
            "step_id": "step_2",
            "title": "理解 AI 決策會議",
            "title_newcomer": "AI 是怎麼幫你選股票的？",
            "description": "AI 透過六大會議進行決策分析。",
            "description_newcomer": "AI 每天跑六個檢查，幫你決定要不要買賣。",
            "key_points": ["晨間策略會議", "新聞分析會議", "風險評估會議", "選股會議", "買���決策會議", "盤後複盤會議"],
            "key_points_newcomer": ["早上的計劃", "白天看新聞", "檢查風險", "選股票", "決定買賣", "晚上複盤"]
        },
        {
            "step_id": "step_3",
            "title": "設定風險參數",
            "title_newcomer": "你要設定風險提醒",
            "description": "請設定您的風險偏好。",
            "description_newcomer": "設定每天最多能虧多少錢。",
            "key_points": ["單日虧損上限", "單筆交易上限", "停損停利規則"],
            "key_points_newcomer": ["一天最多亏多少", "一筆最多買多少", "要不要自動停損"]
        },
        {
            "step_id": "step_4",
            "title": "開始監控",
            "title_newcomer": "可以開始看了",
            "description": "設定完成後，AI 將監控市場並提供建議。",
            "description_newcomer": "設定好之後，AI 就會開始幫你看了。",
            "key_points": ["可在控制面板查看建議", "最後決定需您確認", "可隨時調整參數"],
            "key_points_newcomer": ["在控制面板可以看到", "買賣要你同意", "可以隨時修改設定"]
        }
    ]

    SIGNAL_LIGHTS = {
        "green": {
            "meaning": "正常",
            "meaning_newcomer": "一切正常，可以繼續",
            "description": "系統正常運作，風險在可控範圍內。"
        },
        "yellow": {
            "meaning": "注意",
            "meaning_newcomer": "要注意一下",
            "description": "風險有所上升或接近閾值，建議關注。"
        },
        "red": {
            "meaning": "警告",
            "meaning_newcomer": "要小心了！",
            "description": "風險過高或接近閾值，建議謹慎操作或考慮平倉。"
        }
    }

    def __init__(self, repo_root: Path = None):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self._truth_source: Dict[str, Any] = {}
        self._load_truth_source()

    def _load_truth_source(self) -> None:
        """Load truth source from unified state files."""
        try:
            round_yaml = self.repo_root / "manifests" / "current_round.yaml"
            if round_yaml.exists():
                import yaml
                with open(round_yaml, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    self._truth_source["current_round"] = data.get("current_round", "NONE")
                    self._truth_source["last_completed_round"] = data.get("last_completed_round", "NONE")
                    self._truth_source["phase_state"] = data.get("phase_state", "NONE")
                    self._truth_source["chain_status"] = data.get("chain_status", "UNKNOWN")
                    self._truth_source["auto_run"] = data.get("auto_run", False)
        except Exception as e:
            logger.warning(f"Could not load truth source: {e}")

        try:
            lock_file = self.repo_root / "automation" / "control" / "AUTO_MODE_ACTIVATION_LOCK"
            if lock_file.exists():
                with open(lock_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._truth_source["chain_control_status"] = data.get("chain_control", {}).get("status", "UNKNOWN")
                    self._truth_source["chain_control_reason"] = data.get("chain_control", {}).get("reason", "UNKNOWN")
        except Exception as e:
            logger.warning(f"Could not load activation lock: {e}")

    def get_truth_source_state(self) -> Dict[str, Any]:
        """Get current truth source state (same as backend reads)."""
        return self._truth_source.copy()

    def get_user_mode(self, mode: str = "newcomer") -> Dict[str, Any]:
        """Get configuration for user mode."""
        is_newcomer = mode == "newcomer"
        return {
            "mode": mode,
            "is_newcomer": is_newcomer,
            "terminology": "白話" if is_newcomer else "專業",
            "signal_enabled": True,
            "tutorial_steps": self.TUTORIAL_STEPS if is_newcomer else []
        }

    def explain_term(self, term: str, mode: str = "newcomer") -> str:
        """Get plain language explanation for a term."""
        if term in self.DEFAULT_TERMS:
            return self.DEFAULT_TERMS[term].get(mode, self.DEFAULT_TERMS[term].get("newcomer", ""))
        return f"{term}: 無說明"

    def get_all_terms(self, mode: str = "newcomer") -> Dict[str, str]:
        """Get all terms with explanations in specified mode."""
        result = {}
        for term, explanations in self.DEFAULT_TERMS.items():
            result[term] = explanations.get(mode, explanations.get("newcomer", ""))
        return result

    def get_signal_status(self, status: str = "green") -> Dict[str, str]:
        """Get signal light information."""
        if status in self.SIGNAL_LIGHTS:
            return self.SIGNAL_LIGHTS[status].copy()
        return self.SIGNAL_LIGHTS["green"].copy()

    def get_all_signals(self) -> Dict[str, Dict[str, str]]:
        """Get all signal lights."""
        return self.SIGNAL_LIGHTS.copy()

    def get_tutorial_step(self, step_id: str, mode: str = "newcomer") -> Optional[Dict[str, Any]]:
        """Get specific tutorial step."""
        for step in self.TUTORIAL_STEPS:
            if step["step_id"] == step_id:
                result = step.copy()
                if mode == "newcomer":
                    result["title"] = step.get("title_newcomer", step["title"])
                    result["description"] = step.get("description_newcomer", step["description"])
                    result["key_points"] = step.get("key_points_newcomer", step["key_points"])
                return result
        return None

    def get_tutorial_flow(self, mode: str = "newcomer") -> List[Dict[str, Any]]:
        """Get complete tutorial flow."""
        if mode == "newcomer":
            return [
                {
                    "step_id": step["step_id"],
                    "title": step.get("title_newcomer", step["title"]),
                    "description": step.get("description_newcomer", step["description"]),
                    "key_points": step.get("key_points_newcomer", step["key_points"])
                }
                for step in self.TUTORIAL_STEPS
            ]
        return self.TUTORIAL_STEPS

    def get_key_warnings(self, mode: str = "newcomer") -> List[str]:
        """Get key warnings for users."""
        if mode == "newcomer":
            return [
                "AI 是幫你出主意的，不是幫你買賣的",
                "要設每天最多能虧多少錢",
                "過去賺錢不等於將來會賺錢",
                "���要���全部錢都投入",
                "最後決定要自己做"
            ]
        return [
            "AI 提供決策建議，非直接交易指令",
            "請設置個人風險參數",
            "過去表現不代表未來結果",
            "請勿投入超過承受損失的資金",
            "交易最終決定權在使用者"
        ]

    def render_dashboard(self, user_mode: str = "newcomer") -> Dict[str, Any]:
        """Render complete dashboard from unified truth source (same as backend)."""
        truth_state = self.get_truth_source_state()
        mode_config = self.get_user_mode(user_mode)
        
        return {
            "mode": mode_config["mode"],
            "terminology": mode_config["terminology"],
            "truth_source": truth_state,
            "tutorial": self.get_tutorial_flow(user_mode),
            "signals": self.get_all_signals(),
            "terms": self.get_all_terms(user_mode),
            "warnings": self.get_key_warnings(user_mode)
        }


def get_tutorial_ui(repo_root: Path = None) -> TutorialUI:
    """Factory function to get TutorialUI instance."""
    return TutorialUI(repo_root)