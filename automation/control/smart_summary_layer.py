from datetime import datetime
import json
from pathlib import Path

class SummarySource:
    def __init__(self):
        self.sources = {
            "market": "market_data_feed",
            "system": "system_status",
            "risk": "risk_assessment_engine",
            "next_steps": "workflow_coordinator"
        }

    def get_source(self, category: str) -> str:
        return self.sources.get(category, "unknown")


class SmartSummaryLayer:
    def __init__(self):
        self.source = SummarySource()
        self.categories = ["market", "system", "risk", "next_steps"]
        self.cache = {}

    def generate_summary(self, data: dict, category: str = "market") -> dict:
        if category not in self.categories:
            raise ValueError(f"Invalid category: {category}. Available: {self.categories}")

        source_name = self.source.get_source(category)
        summary_text = ""
        metadata = {}

        if category == "market":
            summary_text = self._generate_market_summary(data)
            metadata = {"price": data.get("price"), "change": data.get("change")}
        elif category == "system":
            summary_text = self._generate_system_summary(data)
            metadata = {"status": data.get("status"), "uptime": data.get("uptime")}
        elif category == "risk":
            summary_text = self._generate_risk_summary(data)
            metadata = {"level": data.get("level"), "factors": data.get("factors")}
        elif category == "next_steps":
            summary_text = self._generate_next_steps_summary(data)
            metadata = {"count": len(data.get("actions", []))}

        return {
            "summary": summary_text,
            "category": category,
            "source": source_name,
            "metadata": metadata,
            "generated_at": "2026-04-27T00:00:00Z"
        }

    def _generate_market_summary(self, data: dict) -> str:
        symbol = data.get("symbol", "N/A")
        price = data.get("price", 0)
        change = data.get("change", 0)
        change_pct = data.get("change_pct", 0)

        direction = "上漲" if change > 0 else "下跌" if change < 0 else "持平"
        return f"{symbol} 價格 {price}，{direction} {abs(change_pct):.2f}%，波動 {data.get('volatility', 0):.2f}%"

    def _generate_system_summary(self, data: dict) -> str:
        status = data.get("status", "unknown")
        uptime = data.get("uptime", 0)
        messages_processed = data.get("messages_processed", 0)

        status_text = "正常" if status == "healthy" else "異常"
        return f"系統狀態 {status_text}，運行 {uptime} 小時，已處理 {messages_processed} 條訊息"

    def _generate_risk_summary(self, data: dict) -> str:
        level = data.get("level", "unknown")
        factors = data.get("factors", [])

        level_text = {"low": "低", "medium": "中", "high": "高"}.get(level, "未知")
        return f"風險等級 {level_text}，監控 {len(factors)} 個風險因子"

    def _generate_next_steps_summary(self, data: dict) -> str:
        actions = data.get("actions", [])
        if not actions:
            return "無待處理動作"

        action_count = len(actions)
        next_action = actions[0] if actions else "無"
        return f"待處理 {action_count} 項，下一步：{next_action}"

    def get_categories(self) -> list:
        return self.categories

    def get_source_info(self, category: str) -> str:
        return self.source.get_source(category)

    def batch_generate(self, data: dict) -> dict:
        results = {}
        for category in self.categories:
            if category in data:
                results[category] = self.generate_summary(data[category], category)
        return results

    def generate_runtime_summary(self, state: dict) -> dict:
        tick_items = list(state.get("ticks", {}).values())
        active_ticks = [t for t in tick_items if t.get("available") and t.get("price")]
        pos_count = len(state.get("positions", {}))
        trade_count = len(state.get("trades_log", []))
        signal_count = len(state.get("signal_history", []))
        agent_count = len(state.get("agents", {}))
        
        market_summary = f"報價 {len(active_ticks)} 檔，漲跌 "
        if active_ticks:
            prices = [t["price"] for t in active_ticks if t.get("price")]
            if prices:
                avg = sum(prices) / len(prices)
                market_summary += f"均價 {avg:.2f}"
        
        position_summary = f"持倉 {pos_count} 口"
        trade_summary = f"成交 {trade_count} 筆"
        signal_summary = f"訊號 {signal_count} 個"
        agent_summary = f"Agent {agent_count} 個"
        
        result = {
            "summary": f"{market_summary} | {position_summary} | {trade_summary} | {signal_summary} | {agent_summary}",
            "category": "runtime_aggregate",
            "source": "trading_engine_runtime",
            "metadata": {
                "active_ticks": len(active_ticks),
                "positions": pos_count,
                "trades": trade_count,
                "signals": signal_count,
                "agents": agent_count,
            },
            "generated_at": datetime.now().isoformat()
        }
        # Side-channel: non-core integration payload
        self._write_side_channel(state, result)
        return result

    def _write_side_channel(self, state: dict, summary_payload: dict) -> None:
        try:
            sc_path = Path("automation/control/candidates/R024-SMART-SUMMARY-LAYER/summary_runtime_state.json")
            sc_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "generated_at": summary_payload.get("generated_at"),
                "category": summary_payload.get("category"),
                "summary": summary_payload.get("summary"),
                "state_snapshot": state
            }
            with sc_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


class SummaryValidator:
    @staticmethod
    def validate_summary_structure(summary: dict) -> bool:
        required_fields = ["summary", "category", "source", "metadata", "generated_at"]
        return all(field in summary for field in required_fields)

    @staticmethod
    def validate_category(summary: dict, expected_category: str) -> bool:
        return summary.get("category") == expected_category

    @staticmethod
    def validate_source(summary: dict, expected_source: str) -> bool:
        return summary.get("source") == expected_source
