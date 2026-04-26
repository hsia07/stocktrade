"""
PHASE2-API-AUTOMODE-R023: 首頁與新手操作體驗強化
Homepage and newcomer experience enhancement.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("homepage_enhancement")


class HomepageContent:
    """Homepage content with newcomer-friendly presentation."""

    FEATURED_SECTIONS = [
        {
            "section_id": "intro",
            "title": "歡迎使用當沖機器人",
            "title_newcomer": "歡迎使用",
            "description": "AI 輔助交易決策系統",
            "description_newcomer": "幫你分析市場、選股票的 AI 系統",
            "icon": "robot"
        },
        {
            "section_id": "status",
            "title": "系統狀態",
            "title_newcomer": "現在怎麼樣？",
            "description": "即時市場與部位狀態",
            "description_newcomer": "今天市場好嗎？我有多少股票？",
            "icon": "chart"
        },
        {
            "section_id": "actions",
            "title": "快速操作",
            "title_newcomer": "要怎麼做？",
            "description": "買賣刷新與設定調整",
            "description_newcomer": "我想買賣、要改設定",
            "icon": "play"
        },
        {
            "section_id": "history",
            "title": "交易紀錄",
            "title_newcomer": "我做過什麼？",
            "description": "歷史交易與績效",
            "description_newcomer": "我今天賺多少？",
            "icon": "history"
        }
    ]

    def __init__(self, user_mode: str = "newcomer"):
        self.user_mode = user_mode

    def get_section(self, section_id: str) -> Optional[Dict[str, Any]]:
        for section in self.FEATURED_SECTIONS:
            if section["section_id"] == section_id:
                return self._adapt_section(section)
        return None

    def _adapt_section(self, section: Dict[str, Any]) -> Dict[str, Any]:
        if self.user_mode == "newcomer":
            return {
                "section_id": section["section_id"],
                "title": section.get("title_newcomer", section["title"]),
                "description": section.get("description_newcomer", section["description"]),
                "icon": section["icon"]
            }
        return section.copy()

    def get_all_sections(self) -> List[Dict[str, Any]]:
        return [self._adapt_section(s) for s in self.FEATURED_SECTIONS]


class NewcomerExperience:
    """Newcomer experience enhancements for reduced confusion."""

    QUICK_GUIDES = [
        {
            "guide_id": "first_time",
            "title": "第一次使用",
            "steps": [
                "打開首頁",
                "看看今天的市場分析",
                "如果有建議，考慮一下",
                "決 定要買賣時，按確認"
            ]
        },
        {
            "guide_id": "checking_status",
            "title": "查看狀態",
            "steps": [
                "看系統狀態區塊",
                "綠色表示正常",
                "黄色表示注意",
                "红色表示警��"
            ]
        },
        {
            "guide_id": "making_trade",
            "title": "如何買賣",
            "steps": [
                "看到 AI 建議",
                "決定是否同意",
                "按確認來執行",
                "可以在歷史看記錄"
            ]
        }
    ]

    def __init__(self):
        pass

    def get_guide(self, guide_id: str) -> Optional[Dict[str, Any]]:
        for guide in self.QUICK_GUIDES:
            if guide["guide_id"] == guide_id:
                return guide
        return None

    def get_all_guides(self) -> List[Dict[str, Any]]:
        return self.QUICK_GUIDES.copy()


class HomepageEnhancement:
    """
    Main class for R023: 首頁與新手操作體驗強化
    
    Provides:
    - Homepage with featured sections
    - Newcomer-friendly descriptions
    - Quick guides
    - Signal indicators
    """

    def __init__(self, repo_root: Path = None, user_mode: str = "newcomer"):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.user_mode = user_mode
        self.homepage = HomepageContent(user_mode)
        self.newcomer_exp = NewcomerExperience()

    def get_homepage_sections(self) -> List[Dict[str, Any]]:
        return self.homepage.get_all_sections()

    def get_quick_guides(self) -> List[Dict[str, Any]]:
        return self.newcomer_exp.get_all_guides()

    def render_homepage(self) -> Dict[str, Any]:
        return {
            "mode": self.user_mode,
            "sections": self.get_homepage_sections(),
            "guides": self.get_quick_guides()
        }


def get_homepage_enhancement(repo_root: Path = None, user_mode: str = "newcomer") -> HomepageEnhancement:
    """Factory function."""
    return HomepageEnhancement(repo_root, user_mode)