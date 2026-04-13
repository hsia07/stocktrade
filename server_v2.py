"""
╔══════════════════════════════════════════════════════════════╗
║   台股 AI 六角色自動交易系統 v2.0                              ║
║   FastAPI + WebSocket + Shioaji + Line/Email 通知             ║
║                                                              ║
║   啟動：python server.py                                      ║
║   排程：自動在 TRADE_START 開始，TRADE_END 停止              ║
╚══════════════════════════════════════════════════════════════╝

pip install fastapi uvicorn shioaji pandas numpy python-dotenv requests schedule
"""

import asyncio, json, logging, os, time, math, smtplib, threading, re
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

try:
    import schedule
except ImportError:
    schedule = None

import requests
import uvicorn
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════
# ① 全域設定
# ══════════════════════════════════════════════════════════════
PAPER_TRADE    = os.getenv("PAPER_TRADE",   "true").lower() == "true"
TOTAL_CAPITAL  = float(os.getenv("TOTAL_CAPITAL", "500000"))
WATCH_LIST     = [s.strip() for s in os.getenv("WATCH_LIST", "2330,2454,2382,3017,2317,2308").split(",") if s.strip()]
DETAIL_SYMBOLS = WATCH_LIST[:]   # 六角色分析 / 回測 / 交易專用精選池
LINE_TOKEN     = os.getenv("LINE_TOKEN",    "")

# 效能優化參數
TICK_INTERVAL = 1          # Tick 產生間隔（秒）
BROADCAST_INTERVAL = 1     # WebSocket 廣播間隔（秒）
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"  # 測試模式：快速生成 K 棒
EMAIL_FROM     = os.getenv("EMAIL_FROM",    "")
EMAIL_TO       = os.getenv("EMAIL_TO",      "")
EMAIL_PASS     = os.getenv("EMAIL_PASS",    "")
EMAIL_SMTP     = os.getenv("EMAIL_SMTP",    "smtp.gmail.com")
EMAIL_PORT     = int(os.getenv("EMAIL_PORT", "587"))
AUTO_TRADE     = os.getenv("AUTO_TRADE",    "true").lower() == "true"
LINE_NOTIFY_ENABLED  = os.getenv("LINE_NOTIFY_ENABLED",  "true").lower() == "true"
EMAIL_NOTIFY_ENABLED = os.getenv("EMAIL_NOTIFY_ENABLED", "true").lower() == "true"
NOTIFY_COOLDOWN_SEC  = int(os.getenv("NOTIFY_COOLDOWN_SEC", "300"))

# 全市場掃描（僅顯示排行，不直接把上千檔都丟進前端）
SCAN_ALL_TW         = os.getenv("SCAN_ALL_TW", "true").lower() == "true"
MARKET_BOARD_LIMIT  = int(os.getenv("MARKET_BOARD_LIMIT", "80"))
SCAN_REFRESH_SEC    = int(os.getenv("SCAN_REFRESH_SEC", "20"))
SCAN_CHUNK_SIZE     = int(os.getenv("SCAN_CHUNK_SIZE", "50"))
UNIVERSE_CACHE_TTL  = int(os.getenv("UNIVERSE_CACHE_TTL", str(60 * 60 * 24)))
REAL_QUOTE_CACHE_MAX_SEC = int(os.getenv("REAL_QUOTE_CACHE_MAX_SEC", "120"))

SYM_NAMES = {
    "2330": "台積電", "2454": "聯發科", "2382": "廣達",
    "3017": "奇鋐",  "2317": "鴻海",  "2308": "台達電",
    "2603": "長榮",  "2881": "富邦金", "2882": "國泰金",
    "0050": "元大台灣50", "0056": "元大高股息", "00878": "國泰永續高股息",
}
DEFAULT_DISPLAY_SYMBOL = DETAIL_SYMBOLS[0] if DETAIL_SYMBOLS else "2330"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("trading.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("TW-AI")


# ══════════════════════════════════════════════════════════════
# ① 學習資料持久化模組 (新增)
# ══════════════════════════════════════════════════════════════
class LearningDataStore:
    """學習資料持久化儲存"""
    
    DATA_DIR = Path("learning_data")
    DATA_DIR.mkdir(exist_ok=True)
    
    @staticmethod
    def _path(name: str) -> Path:
        return LearningDataStore.DATA_DIR / f"{name}.json"
    
    @staticmethod
    def save(name: str, data: list):
        """儲存列表資料"""
        try:
            path = LearningDataStore._path(name)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning(f"儲存失敗 {name}: {e}")
    
    @staticmethod
    def load(name: str, default=None) -> list:
        """載入列表資料"""
        try:
            path = LearningDataStore._path(name)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            log.warning(f"載入失敗 {name}: {e}")
        return default if default is not None else []
    
    @staticmethod
    def append(name: str, item: dict, max_items: int = 1000):
        """新增資料並維持上限"""
        data = LearningDataStore.load(name)
        data.append(item)
        # 只保留最近 max_items 筆
        data = data[-max_items:]
        LearningDataStore.save(name, data)


# ══════════════════════════════════════════════════════════════
# ①-AI 記憶與學習管理
# ══════════════════════════════════════════════════════════════
class AILearningManager:
    """AI 學習管理器 - 讓六大 AI 可學習成長"""
    
    # 學習模式
    MODE_OFFLINE = "offline"      # 離線學習
    MODE_PAPER = "paper"        # 模擬盤學習
    MODE_LIVE = "live"         # 實盤
    MODE_DISABLED = "disabled"   # 關閉
    
    def __init__(self):
        self.mode = self.MODE_PAPER  # 預設模擬盤學習
        
        # 載入歷史資料
        self.decision_log = LearningDataStore.load("decision_log", [])
        self.outcome_log = LearningDataStore.load("outcome_log", [])
        
        # 各 AI 的記憶與權重
        self.agent_memory = LearningDataStore.load("agent_memory", {
            "quant": {"weight": 1.0, "regime_weights": {"bull": 1.0, "bear": 0.5, "neutral": 0.8}, "recent_scores": []},
            "backtest": {"weight": 1.0, "regime_weights": {"bull": 1.0, "bear": 0.5, "neutral": 0.8}, "recent_scores": []},
            "risk": {"weight": 1.5, "regime_weights": {"bull": 1.0, "bear": 1.5, "neutral": 1.2}, "recent_scores": []},
            "signal": {"weight": 1.0, "regime_weights": {"bull": 1.0, "bear": 0.7, "neutral": 0.9}, "recent_scores": []},
            "execution": {"weight": 0.8, "regime_weights": {"bull": 1.0, "bear": 0.6, "neutral": 0.8}, "recent_scores": []},
            "analyst": {"weight": 1.0, "regime_weights": {"bull": 1.2, "bear": 0.8, "neutral": 1.0}, "recent_scores": []},
        })
        
        # 初始化完整結構
        self.init_agent_if_needed()
        
        log.info(f"📚 載入 AI 記憶: {len(self.decision_log)} 筆決策, {len(self.outcome_log)} 筆結果")
    
    def set_mode(self, mode: str):
        """設定學習模式"""
        old = self.mode
        self.mode = mode
        log.info(f"📚 學習模式切換: {old} -> {mode}")
        Notifier.send("學習模式", f"已切換至 {mode}", "info")
    
    def get_mode(self) -> str:
        return self.mode
    
    def init_agent_if_needed(self):
        """初始化完整 agent_memory 結構"""
        default_structure = {
            "weight": 1.0,
            "regime_weights": {"bull": 1.0, "bear": 0.5, "neutral": 0.8},
            "recent_scores": [],
            "regime_stats": {"bull": {"total": 0, "wins": 0}, "bear": {"total": 0, "wins": 0}, "neutral": {"total": 0, "wins": 0}},
            "symbol_stats": {},
            "weight_history": [],
            "confidence_history": [],
        }
        agent_params = {
            "quant": {"factor_weights": {"breakout": 30, "squeeze": 25, "slope": 20}},
            "backtest": {"stop_loss": 0.012, "take_profit": 0.022, "max_hold": 30},
            "risk": {"conservative_mode": 0, "position_scale": 1.0, "halt_threshold": 3},
            "signal": {"threshold": 50, "confidence_base": 60},
            "execution": {"slippage_allow": 0.005, "liquidity_min": 1000, "fill_quality": 1.0},
            "analyst": {"regime_threshold": 1.5, "spike_sensitivity": 2.0},
        }
        for name in ["quant", "backtest", "risk", "signal", "execution", "analyst"]:
            if name not in self.agent_memory:
                self.agent_memory[name] = default_structure.copy()
            else:
                for k, v in default_structure.items():
                    if k not in self.agent_memory[name]:
                        self.agent_memory[name][k] = v
            if name in agent_params:
                if "params" not in self.agent_memory[name]:
                    self.agent_memory[name]["params"] = agent_params[name]
                else:
                    for k, v in agent_params[name].items():
                        if k not in self.agent_memory[name]["params"]:
                            self.agent_memory[name]["params"][k] = v
        LearningDataStore.save("agent_memory", self.agent_memory)
    
    def log_decision(self, data: dict):
        """記錄決策"""
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["mode"] = self.mode
        self.decision_log.append(data)
        LearningDataStore.append("decision_log", data, 500)
    
    def log_outcome(self, data: dict):
        """記錄結果"""
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["mode"] = self.mode
        self.outcome_log.append(data)
        LearningDataStore.append("outcome_log", data, 500)
        
        # 根據結果更新 AI 權重
        if self.mode != self.MODE_DISABLED:
            self._update_weights(data)
    
    def _update_weights(self, outcome: dict):
        """根據交易結果更新 AI 權重與參數 (平滑調整)"""
        pnl = outcome.get("pnl", 0)
        success = pnl > 0
        regime = outcome.get("regime", "neutral")
        error_type = outcome.get("error_type", "")
        
        # 更新每個 AI 的權重與參數
        ai_scores = outcome.get("ai_scores", {})
        for ai_name, score in ai_scores.items():
            if ai_name in self.agent_memory:
                mem = self.agent_memory[ai_name]
                mem.setdefault("recent_scores", [])
                mem.setdefault("regime_stats", {"bull": {"total": 0, "wins": 0}, "bear": {"total": 0, "wins": 0}, "neutral": {"total": 0, "wins": 0}})
                mem.setdefault("params", {})
                
                # 更新最近分數
                score_val = 1.0 if success else 0.0
                mem["recent_scores"].append(score_val)
                mem["recent_scores"] = mem["recent_scores"][-20:]
                
                # 更新 regime 統計
                if regime in mem["regime_stats"]:
                    mem["regime_stats"][regime]["total"] = mem["regime_stats"][regime].get("total", 0) + 1
                    if success:
                        mem["regime_stats"][regime]["wins"] = mem["regime_stats"][regime].get("wins", 0) + 1
                
                # 計算最近勝率
                win_rate = 0.5
                if len(mem["recent_scores"]) >= 5:
                    win_rate = sum(mem["recent_scores"]) / len(mem["recent_scores"])
                    delta = 0.1 if win_rate > 0.6 else (-0.1 if win_rate < 0.4 else 0)
                    old_weight = mem.get("weight", 1.0)
                    mem["weight"] = max(0.3, min(2.0, old_weight + delta))
                    
                    # 記錄權重歷史
                    mem.setdefault("weight_history", [])
                    mem["weight_history"].append({"ts": datetime.now().strftime("%H:%M:%S"), "weight": mem["weight"]})
                    mem["weight_history"] = mem["weight_history"][-50:]
                
                # 根據 outcome 更新 AI 特定參數
                params = mem.get("params", {})
                if ai_name == "backtest":
                    if error_type == "stop_loss":
                        sl = params.get("stop_loss", 0.012)
                        params["stop_loss"] = min(sl * 1.2, 0.025)
                    elif error_type == "time_exit":
                        mh = params.get("max_hold", 30)
                        params["max_hold"] = max(mh - 5, 10)
                    elif success and error_type == "take_profit":
                        tp = params.get("take_profit", 0.022)
                        params["take_profit"] = max(tp * 0.9, 0.015)
                elif ai_name == "risk":
                    if error_type == "stop_loss" or error_type == "negative_pnl":
                        cm = params.get("conservative_mode", 0)
                        params["conservative_mode"] = min(cm + 0.1, 1.0)
                    elif success:
                        cm = params.get("conservative_mode", 0)
                        params["conservative_mode"] = max(cm - 0.05, 0)
                elif ai_name == "signal":
                    if error_type in ("stop_loss", "negative_pnl"):
                        th = params.get("threshold", 50)
                        params["threshold"] = min(th + 5, 70)
                    elif success:
                        th = params.get("threshold", 50)
                        params["threshold"] = max(th - 2, 40)
                elif ai_name == "execution":
                    if error_type == "negative_pnl":
                        sa = params.get("slippage_allow", 0.005)
                        params["slippage_allow"] = min(sa * 1.2, 0.015)
                elif ai_name == "analyst":
                    if success:
                        rt = params.get("regime_threshold", 1.5)
                        params["regime_threshold"] = max(rt - 0.1, 0.5)
                
                mem["params"] = params
                log.info(f"📈 {ai_name} 權重: {mem['weight']:.2f} 勝率:{win_rate*100:.0f}% | params:{json.dumps(params)}")
        
        # 儲存更新後的權重
        LearningDataStore.save("agent_memory", self.agent_memory)
    
    def get_agent_info(self, ai_name: str = None) -> dict:
        """取得 AI 資訊"""
        if ai_name:
            return self.agent_memory.get(ai_name, {})
        return self.agent_memory
    
    def get_consensus_score(self, ai_scores: dict, regime: str = "neutral") -> float:
        """計算六大 AI 共識分數"""
        total_weight = 0.0
        weighted_score = 0.0
        
        for ai_name, score in ai_scores.items():
            mem = self.agent_memory.get(ai_name, {})
            base_weight = mem.get("weight", 1.0)
            regime_weight = mem.get("regime_weights", {}).get(regime, 1.0)
            weight = base_weight * regime_weight
            
            weighted_score += score * weight
            total_weight += weight
        
        if total_weight <= 0:
            return 0.5
        
        return weighted_score / total_weight
    
    def can_trade(self) -> bool:
        """檢查是否可以交易"""
        if self.mode == self.MODE_DISABLED:
            return False
        if self.mode == self.MODE_LIVE and not PAPER_TRADE:
            return True
        if self.mode == self.MODE_PAPER:
            return True
        return False
    
    def get_status(self) -> dict:
        """取得學習系統狀態"""
        return {
            "mode": self.mode,
            "decisions": len(self.decision_log),
            "outcomes": len(self.outcome_log),
            "agents": {k: {"weight": v["weight"], "recent": v["recent_scores"][-5:]} 
                      for k, v in self.agent_memory.items()}
        }


# 建立全域學習管理器
learning_mgr = AILearningManager()


# ══════════════════════════════════════════════════════════════
# ② 通知模組（Line + Email）- 改進版：失敗保護、次數限制、避免狂刷
# ══════════════════════════════════════════════════════════════
class Notifier:
    """統一通知介面，支援冷卻、失敗保護與 UTF-8 郵件標題"""

    _cooldowns: dict[str, float] = {}
    _line_fail_count: int = 0
    _email_fail_count: int = 0
    _line_disabled: bool = False
    _email_disabled: bool = False
    _line_disabled_reason: Optional[str] = None
    _email_disabled_reason: Optional[str] = None
    MAX_FAILURES = 3  # 失敗 3 次後停用

    @staticmethod
    def _can_send(key: str, cooldown_sec: int) -> bool:
        if cooldown_sec <= 0:
            return True
        now = time.time()
        last = Notifier._cooldowns.get(key, 0.0)
        if now - last < cooldown_sec:
            return False
        Notifier._cooldowns[key] = now
        return True

    @staticmethod
    def send(subject: str, body: str, level: str = "info", cooldown_key: Optional[str] = None, cooldown_sec: Optional[int] = None):
        """level: info / ok / warn / alert"""
        # 記錄到 log，但不刷通知
        prefix = {"info": "ℹ️", "ok": "✅", "warn": "⚠️", "alert": "🚨"}.get(level, "ℹ️")
        log.info(f"[通知] {subject}")

        # 冷卻檢查
        key = cooldown_key or f"{level}:{subject}"
        sec = NOTIFY_COOLDOWN_SEC if cooldown_sec is None else cooldown_sec
        if sec and not Notifier._can_send(key, sec):
            return

        # 嘗試發送
        if LINE_NOTIFY_ENABLED and LINE_TOKEN and not Notifier._line_disabled:
            Notifier._line(f"{prefix} {subject}\n\n{body}"[:1000])
        if EMAIL_NOTIFY_ENABLED and EMAIL_FROM and EMAIL_TO and EMAIL_PASS and not Notifier._email_disabled:
            Notifier._email(f"{prefix} {subject}", body)

    @staticmethod
    def _line(message: str):
        if Notifier._line_disabled:
            return
        try:
            requests.post(
                "https://notify-api.line.me/api/notify",
                headers={"Authorization": f"Bearer {LINE_TOKEN}"},
                data={"message": f"\n{message}"},
                timeout=8,
            )
            Notifier._line_fail_count = 0  # 成功就重置計數
        except Exception as e:
            Notifier._line_fail_count += 1
            if Notifier._line_fail_count >= Notifier.MAX_FAILURES:
                Notifier._line_disabled = True
                Notifier._line_disabled_reason = f"連續失敗 {Notifier._line_fail_count} 次"
                log.warning(f"⚠️ Line 通知已停用：{Notifier._line_disabled_reason}")
            else:
                log.debug(f"Line 通知失敗 (第{Notifier._line_fail_count}次): {e}")

    @staticmethod
    def _email(subject: str, body: str):
        if Notifier._email_disabled:
            return
        try:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_FROM
            msg["To"] = EMAIL_TO
            msg["Subject"] = str(Header(subject, "utf-8"))
            msg.attach(MIMEText(body, "plain", "utf-8"))
            with smtplib.SMTP(EMAIL_SMTP, EMAIL_PORT) as s:
                s.starttls()
                s.login(EMAIL_FROM, EMAIL_PASS)
                s.send_message(msg)
            Notifier._email_fail_count = 0
        except Exception as e:
            Notifier._email_fail_count += 1
            if Notifier._email_fail_count >= Notifier.MAX_FAILURES:
                Notifier._email_disabled = True
                Notifier._email_disabled_reason = f"連續失敗 {Notifier._email_fail_count} 次"
                log.warning(f"⚠️ Email 通知已停用：{Notifier._email_disabled_reason}")
            else:
                log.debug(f"Email 通知失敗 (第{Notifier._email_fail_count}次): {e}")


# ══════════════════════════════════════════════════════════════
# ③ 工具：全市場股票清單 + 全市場掃描排行
# ══════════════════════════════════════════════════════════════
UNIVERSE_CACHE_PATH = os.path.join("data", "tw_universe_cache.json")


def _safe_float(v, default=0.0):
    try:
        if v in (None, "", "-"):
            return default
        return float(str(v).replace(",", ""))
    except Exception:
        return default


def _safe_int(v, default=0):
    try:
        if v in (None, "", "-"):
            return default
        return int(float(str(v).replace(",", "")))
    except Exception:
        return default


class TaiwanMarketUniverse:
    """建立台股上市/上櫃股票池。失敗時退回精選池，避免整套系統無法啟動。"""

    URL = "https://isin.twse.com.tw/isin/C_public.jsp"
    MODE_MAP = {"2": "tse", "4": "otc"}

    @staticmethod
    def _parse_first_col(cell: str):
        s = str(cell).replace("　", " ").strip()
        m = re.match(r'^(\d{4,6})\s+(.+)$', s)
        if not m:
            return None, None
        return m.group(1), m.group(2).strip()

    @classmethod
    def _fetch_mode(cls, mode: str):
        tables = pd.read_html(f"{cls.URL}?strMode={mode}", encoding="big5hkscs")
        if not tables:
            return []
        rows = []
        df = tables[0]
        first_col = df.columns[0]
        for val in df[first_col].tolist():
            code, name = cls._parse_first_col(val)
            if not code:
                continue
            rows.append({"symbol": code, "name": name, "market": cls.MODE_MAP[mode]})
        return rows

    @classmethod
    def load(cls):
        os.makedirs("data", exist_ok=True)
        cache_path = Path(UNIVERSE_CACHE_PATH)
        if cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age <= UNIVERSE_CACHE_TTL:
                try:
                    data = json.loads(cache_path.read_text(encoding="utf-8"))
                    if data:
                        return data
                except Exception:
                    pass
        data = []
        try:
            for mode in ("2", "4"):
                data.extend(cls._fetch_mode(mode))
        except Exception as e:
            log.warning(f"股票池下載失敗，改用快取/精選池：{e}")
            if cache_path.exists():
                try:
                    return json.loads(cache_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            return [{"symbol": s, "name": SYM_NAMES.get(s, s), "market": "tse"} for s in DETAIL_SYMBOLS]
        dedup = {}
        for row in data:
            sym = row["symbol"]
            if sym.isdigit():
                dedup[sym] = row
        final = list(dedup.values())
        try:
            cache_path.write_text(json.dumps(final, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        return final


class MarketScanner:
    """全市場掃描：大量抓即時報價，但前端只顯示排序後前 N 檔。"""

    def __init__(self, universe_rows: list[dict]):
        self.universe_rows = universe_rows or []
        self.symbol_meta = {r["symbol"]: r for r in self.universe_rows}
        self.names = {r["symbol"]: r.get("name", r["symbol"]) for r in self.universe_rows}
        self.market_board: list[dict] = []
        self.quote_cache: dict[str, dict] = {}
        self.last_refresh = 0.0

    def _build_chunks(self):
        exchs = []
        for row in self.universe_rows:
            sym = row.get("symbol")
            market = row.get("market")
            if not sym or market not in {"tse", "otc"}:
                continue
            exchs.append(f"{market}_{sym}.tw")
        for i in range(0, len(exchs), SCAN_CHUNK_SIZE):
            yield exchs[i:i + SCAN_CHUNK_SIZE]

    def refresh(self):
        if not self.universe_rows:
            self.market_board = []
            return []
        now = time.time()
        if self.market_board and now - self.last_refresh < SCAN_REFRESH_SEC:
            return self.market_board
        results = []
        try:
            for chunk in self._build_chunks():
                url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
                params = {"ex_ch": "|".join(chunk), "json": 1, "delay": 0}
                resp = requests.get(url, params=params, timeout=10)
                payload = resp.json()
                for item in payload.get("msgArray", []):
                    sym = str(item.get("c", "")).strip()
                    price = _safe_float(item.get("z"), 0)
                    if not sym or price <= 0:
                        continue
                    ref = _safe_float(item.get("y"), price)
                    volume = _safe_int(item.get("tv"), 0)
                    bid_raw = (item.get("b") or "").split("_")[0]
                    ask_raw = (item.get("a") or "").split("_")[0]
                    bid = _safe_float(bid_raw, max(price - 0.5, 0))
                    ask = _safe_float(ask_raw, price + 0.5)
                    change = price - ref
                    change_pct = (change / ref * 100) if ref else 0.0
                    row = {
                        "symbol": sym,
                        "name": self.names.get(sym) or item.get("n") or sym,
                        "price": round(price, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "volume": volume,
                        "bid": round(bid, 2),
                        "ask": round(ask, 2),
                        "market": self.symbol_meta.get(sym, {}).get("market", "tse"),
                    }
                    score = abs(change_pct) * 4 + min(volume / 1000, 20)
                    row["score"] = round(score, 3)
                    results.append(row)
                    self.quote_cache[sym] = row
        except Exception as e:
            log.warning(f"全市場掃描失敗：{e}")
            return self.market_board
        results.sort(key=lambda x: (x["score"], abs(x["change_pct"]), x["volume"]), reverse=True)
        self.market_board = results[:MARKET_BOARD_LIMIT]
        self.last_refresh = now
        return self.market_board

# ══════════════════════════════════════════════════════════════
# ③ 資料模型
# ══════════════════════════════════════════════════════════════
class Direction(str, Enum):
    LONG  = "long"
    SHORT = "short"
    NONE  = "none"

@dataclass
class Signal:
    symbol:      str
    direction:   Direction
    entry_price: float
    stop_loss:   float
    target_1:    float
    target_2:    float
    confidence:  float
    reason:      str
    timestamp:   str
    ai_source:   str = ""  # 來源 AI

@dataclass
class AgentReport:
    role:      str
    icon:      str
    status:    str      # ok | warn | alert | idle
    summary:   str
    details:   list
    timestamp: str = ""
    score:     float = 50.0  # AI 評分 0-100
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")

@dataclass
class TradeRecord:
    id:         str
    symbol:     str
    direction:  str
    entry:      float
    exit:       float
    lots:       int
    pnl:        float
    reason:     str
    open_time:  str
    close_time: str

@dataclass
class BacktestResult:
    symbol:        str
    total_trades:  int
    win_rate:      float
    profit_factor: float
    avg_win:       float
    avg_loss:      float
    max_drawdown:  float
    total_pnl:     float
    equity_curve:  list   # [{idx, cum_pnl}] 給前端畫圖
    monthly_pnl:   list   # [{month, pnl}]


# ══════════════════════════════════════════════════════════════
# ④ 角色一：量化研究員
# ══════════════════════════════════════════════════════════════
class QuantResearcher:
    def __init__(self):
        self.alpha_scores = {}

    def analyze(self, symbol: str, bars: list, params: dict = None) -> AgentReport:
        if len(bars) < 20:
            return AgentReport("量化研究員", "🔬", "idle", "資料累積中", ["等待 20 根 K 棒…"])

        # 取得學習參數
        fw = params or {"breakout": 30, "squeeze": 25, "slope": 20}
        w_breakout = fw.get("breakout", 30)
        w_squeeze = fw.get("squeeze", 25)
        w_slope = fw.get("slope", 20)

        closes  = [b["close"]  for b in bars]
        volumes = [b["volume"] for b in bars]
        highs   = [b["high"]   for b in bars]

        # Alpha 1：布林帶壓縮（低波動後爆發）
        ma20   = sum(closes[-20:]) / 20
        std20  = (sum((c - ma20) ** 2 for c in closes[-20:]) / 20) ** 0.5
        bb_w   = std20 * 2 / ma20 * 100
        squeeze = bb_w < 3.5

        # Alpha 2：20 日新高突破
        h20      = max(highs[-21:-1])
        breakout = closes[-1] > h20

        # Alpha 3：短期均線向上斜率
        e5_now  = sum(closes[-5:]) / 5
        e5_prev = sum(closes[-8:-3]) / 5
        slope   = (e5_now - e5_prev) / e5_prev * 100

        # Alpha 4：量價背離（爆量不漲 → 警示）
        avg_v5 = sum(volumes[-6:-1]) / 5
        vol_r  = volumes[-1] / (avg_v5 + 1)
        p_chg  = (closes[-1] - closes[-5]) / closes[-5] * 100
        diverge = vol_r > 2 and p_chg < -0.5

        score = 0
        findings = []
        if breakout:  score += w_breakout; findings.append(f"✅ 20日新高突破 {closes[-1]:.1f} > {h20:.1f}")
        if squeeze:   score += w_squeeze; findings.append(f"⚡ 布林帶壓縮 {bb_w:.1f}%，蓄勢待發")
        if slope > 0.3: score += w_slope; findings.append(f"📈 短期均線上斜 +{slope:.2f}%")
        if diverge:   score -= 25; findings.append(f"⚠️ 量價背離：量增 {vol_r:.1f}x 但價跌 {p_chg:.1f}%")
        if not findings: findings.append("目前無明顯 Alpha 訊號")

        self.alpha_scores[symbol] = score
        status = "ok" if score >= 40 else "warn" if score >= 10 else "idle"
        return AgentReport("量化研究員", "🔬", status, f"{symbol} Alpha {score}/75", findings, score=score)


# ══════════════════════════════════════════════════════════════
# ⑤ 角色二：回測工程師（含完整回測資料給視覺化）
# ══════════════════════════════════════════════════════════════
class Backtester:
    def __init__(self):
        self.results: dict[str, BacktestResult] = {}

    def run(self, symbol: str, bars: list, params: dict = None) -> tuple[AgentReport, Optional[BacktestResult]]:
        if len(bars) < 30:
            return AgentReport("回測工程師", "📊", "idle", "資料不足", ["需要 30 根 K 棒"]), None

        # 取得學習參數
        bp = params or {"stop_loss": 0.012, "take_profit": 0.022, "max_hold": 30}
        stop_pct = bp.get("stop_loss", 0.012)
        target_pct = bp.get("take_profit", 0.022)
        max_hold = bp.get("max_hold", 30)

        closes = [b["close"] for b in bars]
        trades, equity, cum = [], [], 0
        in_pos = None

        for i in range(20, len(closes)):
            w   = closes[:i+1]
            e5  = sum(w[-5:]) / 5
            e20 = sum(w[-20:]) / 20

            if in_pos is None and e5 > e20 * 1.002:
                in_pos = {"entry": closes[i], "idx": i}

            elif in_pos:
                held = i - in_pos["idx"]
                hit_stop   = closes[i] < in_pos["entry"] * (1 - stop_pct)
                hit_target = closes[i] > in_pos["entry"] * (1 + target_pct)
                if hit_stop or hit_target or held >= max_hold:
                    pnl = closes[i] - in_pos["entry"]
                    cum += pnl
                    trades.append({"pnl": pnl, "reason": "stop" if hit_stop else "target" if hit_target else "timeout"})
                    equity.append({"idx": len(trades), "cum_pnl": round(cum, 2)})
                    in_pos = None

        if not trades:
            return AgentReport("回測工程師", "📊", "idle", "無交易觸發", ["條件未達"]), None

        pnl_list = [t["pnl"] for t in trades]
        wins     = [p for p in pnl_list if p > 0]
        losses   = [p for p in pnl_list if p < 0]
        wr       = len(wins) / len(trades) * 100
        pf       = abs(sum(wins) / sum(losses)) if losses else 99.0
        avg_w    = sum(wins)   / len(wins)   if wins   else 0
        avg_l    = sum(losses) / len(losses) if losses else 0

        # 最大回撤
        peak, dd, max_dd = 0, 0, 0
        run = 0
        for p in pnl_list:
            run += p
            peak   = max(peak, run)
            dd     = run - peak
            max_dd = min(max_dd, dd)

        # 月度損益（模擬，依 K 棒索引分段）
        chunk = max(len(trades) // 4, 1)
        monthly = [
            {"month": f"第{i+1}段", "pnl": round(sum(pnl_list[i*chunk:(i+1)*chunk]), 2)}
            for i in range(4)
        ]

        res = BacktestResult(
            symbol=symbol, total_trades=len(trades),
            win_rate=round(wr, 1), profit_factor=round(pf, 2),
            avg_win=round(avg_w, 2), avg_loss=round(avg_l, 2),
            max_drawdown=round(max_dd, 2), total_pnl=round(sum(pnl_list), 2),
            equity_curve=equity, monthly_pnl=monthly,
        )
        self.results[symbol] = res
        status = "ok" if wr > 55 and pf > 1.5 else "warn"

        return AgentReport(
            "回測工程師", "📊", status,
            f"{symbol} 勝率 {wr:.0f}% | 盈虧比 {pf:.1f}",
            [
                f"總交易筆數：{len(trades)}",
                f"勝率：{wr:.1f}%",
                f"盈虧比：{pf:.2f}",
                f"平均獲利：+{avg_w:.2f}  |  平均虧損：{avg_l:.2f}",
                f"最大回撤：{max_dd:.2f}",
                f"累計損益：{sum(pnl_list):+.2f}",
            ],
            score=min(100, wr)
        ), res


# ══════════════════════════════════════════════════════════════
# ⑥ 角色三：風控官
# ══════════════════════════════════════════════════════════════
class RiskOfficer:
    # ── 風控參數（可透過 .env 覆蓋）──
    MAX_DAILY_LOSS   = float(os.getenv("MAX_DAILY_LOSS",  "5000"))
    MAX_SINGLE_LOSS  = float(os.getenv("MAX_SINGLE_LOSS", "1500"))
    MAX_TRADES       = int(os.getenv("MAX_TRADES",        "6"))
    MAX_POSITIONS    = int(os.getenv("MAX_POSITIONS",     "2"))
    MAX_CONSEC_LOSS  = int(os.getenv("MAX_CONSEC_LOSS",   "3"))
    MIN_CONFIDENCE   = float(os.getenv("MIN_CONFIDENCE",  "65"))
    TRADE_START      = os.getenv("TRADE_START",  "09:10")
    TRADE_END        = os.getenv("TRADE_END",    "13:00")
    FORCE_CLOSE      = os.getenv("FORCE_CLOSE",  "13:20")
    MAX_CHASE_PCT    = float(os.getenv("MAX_CHASE_PCT",   "0.005"))

    def __init__(self):
        self.daily_pnl        = 0.0
        self.daily_trades     = 0
        self.consecutive_loss = 0
        self.open_positions: dict = {}
        self.is_halted        = False
        self.halt_reason      = ""

    def reset_daily(self):
        self.daily_pnl, self.daily_trades = 0.0, 0
        self.consecutive_loss = 0
        self.open_positions   = {}
        self.is_halted        = False
        self.halt_reason      = ""
        Notifier.send("風控重置", "每日風控統計已重置，交易系統開始運行", "info")

    def can_enter(self, signal: Signal, price: float) -> tuple[bool, str]:
        now = datetime.now().strftime("%H:%M")
        checks = [
            (not self.is_halted,                           f"系統停機：{self.halt_reason}"),
            (self.TRADE_START <= now <= self.TRADE_END,    f"非交易時段 {self.TRADE_START}~{self.TRADE_END}"),
            (self.daily_trades < self.MAX_TRADES,          f"已達單日 {self.MAX_TRADES} 筆"),
            (self.daily_pnl > -self.MAX_DAILY_LOSS,        f"達單日虧損上限 -{self.MAX_DAILY_LOSS}"),
            (len(self.open_positions) < self.MAX_POSITIONS,f"已有 {self.MAX_POSITIONS} 持倉"),
            (signal.symbol not in self.open_positions,     f"{signal.symbol} 已有持倉"),
            (signal.confidence >= self.MIN_CONFIDENCE,     f"信心度 {signal.confidence:.0f} < {self.MIN_CONFIDENCE}"),
            (self.consecutive_loss < self.MAX_CONSEC_LOSS, f"連敗 {self.consecutive_loss} 次"),
            (abs(price - signal.entry_price) / signal.entry_price < self.MAX_CHASE_PCT, "追價超過限制"),
        ]
        for ok, reason in checks:
            if not ok:
                return False, reason
        return True, "OK"

    def calc_lots(self, signal: Signal, price: float, params: dict = None) -> int:
        # 取得學習參數
        ps = params or {"conservative_mode": 0, "position_scale": 1.0}
        scale = ps.get("position_scale", 1.0)
        cons = ps.get("conservative_mode", 0)
        
        risk = abs(price - signal.stop_loss)
        if risk <= 0:
            return 0
        by_loss    = int(self.MAX_SINGLE_LOSS / risk)
        by_capital = int(TOTAL_CAPITAL * 0.25 * scale / (price * 1000))
        max_lots = 3 if cons < 0.5 else 2
        return max(min(by_loss, by_capital, max_lots), 0)

    def on_entry(self, signal: Signal, lots: int, price: float, ai_scores: dict = None, regime: str = "neutral"):
        self.daily_trades += 1
        self.open_positions[signal.symbol] = {
            "direction": signal.direction, "entry": price,
            "lots": lots, "stop": signal.stop_loss,
            "t1": signal.target_1, "t2": signal.target_2,
            "partial": False,
            "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ai_scores": ai_scores or {},
            "regime": regime,
        }

    def on_exit(self, symbol: str, pnl: float):
        self.daily_pnl += pnl
        self.open_positions.pop(symbol, None)
        if pnl < 0:
            self.consecutive_loss += 1
            if self.consecutive_loss >= self.MAX_CONSEC_LOSS:
                self.is_halted   = True
                self.halt_reason = f"連敗 {self.consecutive_loss} 次"
                Notifier.send("風控停機", f"已連續虧損 {self.consecutive_loss} 次，系統自動暫停交易\n今日損益：NT$ {self.daily_pnl:+.0f}", "alert")
        else:
            self.consecutive_loss = 0

    def get_report(self) -> AgentReport:
        remain = self.MAX_DAILY_LOSS + self.daily_pnl
        status = "alert" if self.is_halted else "warn" if remain < 1500 else "ok"
        return AgentReport("風控官", "🛡️", status, f"剩餘虧損額度 NT${remain:.0f}", [
            f"今日損益：NT$ {self.daily_pnl:+.0f}",
            f"剩餘虧損額度：NT$ {remain:.0f}",
            f"剩餘交易次數：{self.MAX_TRADES - self.daily_trades}",
            f"當前持倉：{len(self.open_positions)} / {self.MAX_POSITIONS}",
            f"連敗次數：{self.consecutive_loss} / {self.MAX_CONSEC_LOSS}",
            f"{'🔴 停機：' + self.halt_reason if self.is_halted else '🟢 正常運行'}",
        ])


# ══════════════════════════════════════════════════════════════
# ⑦ 角色四：信號工程師
# ══════════════════════════════════════════════════════════════
class SignalEngineer:
    def __init__(self):
        self._vwap: dict = {}
        self._signal_history: list = []

    def reset_vwap(self, symbol: str):
        self._vwap[symbol] = {"pv": 0.0, "vol": 0}

    def update_vwap(self, symbol: str, bar: dict):
        d = self._vwap.setdefault(symbol, {"pv": 0.0, "vol": 0})
        mid = (bar["high"] + bar["low"] + bar["close"]) / 3
        d["pv"]  += mid * bar["volume"]
        d["vol"] += bar["volume"]

    def vwap(self, symbol: str) -> float:
        d = self._vwap.get(symbol, {})
        return d["pv"] / d["vol"] if d.get("vol") else 0

    @staticmethod
    def _ema(closes: list, span: int) -> float:
        k, e = 2 / (span + 1), closes[0]
        for c in closes[1:]:
            e = c * k + e * (1 - k)
        return e

    @staticmethod
    def _rsi(closes: list, n: int = 14) -> float:
        if len(closes) < n + 1:
            return 50
        d = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        ag = sum(max(x, 0) for x in d[-n:]) / n
        al = sum(-min(x, 0) for x in d[-n:]) / n
        return 100 if al == 0 else 100 - 100 / (1 + ag / al)

    @staticmethod
    def _macd(closes: list) -> tuple:
        if len(closes) < 26:
            return 0, 0, 0
        ema12 = SignalEngineer._ema(closes[-12:], 12)
        ema26 = SignalEngineer._ema(closes[-26:], 26)
        macd = ema12 - ema26
        signal = SignalEngineer._ema([macd] * 9, 9) if macd else 0
        histogram = macd - signal if signal else 0
        return macd, signal, histogram

    @staticmethod
    def _kd(bars: list) -> tuple:
        if len(bars) < 9:
            return 50, 50
        lows = [b["low"] for b in bars[-9:]]
        highs = [b["high"] for b in bars[-9:]]
        rsv = (bars[-1]["close"] - min(lows)) / (max(highs) - min(lows) + 0.001) * 100
        k = rsv
        d = k * 0.5 + 50 * 0.5
        return k, d

    @staticmethod
    def _bollinger(bars: list) -> tuple:
        closes = [b["close"] for b in bars[-20:]]
        if len(closes) < 20:
            return 0, 0, 0
        ma = sum(closes) / 20
        std = (sum((c - ma) ** 2 for c in closes) / 20) ** 0.5
        upper = ma + 2 * std
        lower = ma - 2 * std
        return upper, ma, lower

    @staticmethod
    def _atr(bars: list, n: int = 14) -> float:
        trs = [max(b["high"] - b["low"],
                   abs(b["high"] - bars[i-1]["close"]),
                   abs(b["low"]  - bars[i-1]["close"])) for i, b in enumerate(bars) if i > 0]
        return sum(trs[-n:]) / min(len(trs), n) if trs else 1

    def evaluate(self, symbol: str, bars: list, tick: dict, order_book: dict, params: dict = None) -> tuple[Optional[Signal], AgentReport]:
        if len(bars) < 20:
            return None, AgentReport("信號工程師", "⚡", "idle", "資料累積中", ["等待 20 根 K 棒…"])

        # 取得學習參數
        sp = params or {"threshold": 50, "confidence_base": 60}
        threshold = sp.get("threshold", 50)
        conf_base = sp.get("confidence_base", 60)

        closes = [b["close"] for b in bars]
        price  = tick.get("price", closes[-1])
        vwap   = self.vwap(symbol)
        ema5   = self._ema(closes[-10:], 5)
        ema20  = self._ema(closes[-25:], 20)
        rsi    = self._rsi(closes)
        atr    = self._atr(bars)
        vol_r  = bars[-1]["volume"] / (sum(b["volume"] for b in bars[-6:-1]) / 5 + 1)
        bid_v  = order_book.get("bid_vol", 100)
        ask_v  = order_book.get("ask_vol", 100)
        macd, macd_sig, macd_hist = self._macd(closes)
        k, d = self._kd(bars)
        bb_upper, bb_mid, bb_lower = self._bollinger(bars)

        lc = dict(above_vwap=price>vwap, ema_bull=ema5>ema20, rsi_ok=45<=rsi<=70, vol=vol_r>=1.5, bid_dom=bid_v>ask_v*1.4)
        sc = dict(below_vwap=price<vwap, ema_bear=ema5<ema20, rsi_ok=30<=rsi<=55, vol=vol_r>=1.5, ask_dom=ask_v>bid_v*1.4)
        ls, ss = sum(lc.values()), sum(sc.values())
        bonus  = (10 if vol_r > 2.5 else 0) + (8 if rsi > 65 and ls == 5 else 0) + (8 if rsi < 35 and ss == 5 else 0)

        lines = [
            f"VWAP {vwap:.2f} | 現價 {price:.2f}",
            f"EMA5 {ema5:.2f} | EMA20 {ema20:.2f}",
            f"RSI {rsi:.1f} | ATR {atr:.2f}",
            f"MACD {macd:.2f} ({macd_sig:.2f}) | K {k:.1f} D{d:.1f}",
            f"BB 上 {bb_upper:.2f}/{bb_lower:.2f} | 量比 {vol_r:.1f}x",
            f"多頭{ls}/5 | 空頭{ss}/5",
        ]
        signal = None

        if ls == 5:
            conf   = min(conf_base + bonus, 95)
            signal = Signal(symbol, Direction.LONG, price,
                            round(price - atr*1.2, 2), round(price + atr*1.5, 2), round(price + atr*2.8, 2),
                            conf, "多頭全條件", datetime.now().strftime("%H:%M:%S"), "signal")
            lines.append(f"🟢 多頭信號 信心度 {conf:.0f}% | 止損 {signal.stop_loss} | 目標 {signal.target_1}/{signal.target_2}")
            rep = AgentReport("信號工程師", "⚡", "ok", f"🟢 {symbol} 多頭 {conf:.0f}%", lines)
            self._signal_history.append(asdict(signal))

        elif ss == 5:
            conf   = min(conf_base + bonus, 95)
            signal = Signal(symbol, Direction.SHORT, price,
                            round(price + atr*1.2, 2), round(price - atr*1.5, 2), round(price - atr*2.8, 2),
                            conf, "空頭全條件", datetime.now().strftime("%H:%M:%S"), "signal")
            lines.append(f"🔴 空頭信號 信心度 {conf:.0f}% | 止損 {signal.stop_loss} | 目標 {signal.target_1}/{signal.target_2}")
            rep = AgentReport("信號工程師", "⚡", "alert", f"🔴 {symbol} 空頭 {conf:.0f}%", lines)
            self._signal_history.append(asdict(signal))

        else:
            rep = AgentReport("信號工程師", "⚡", "idle", f"{symbol} 觀望中（多{ls}/空{ss}）", lines)

        return signal, rep

    def get_history(self) -> list:
        return self._signal_history[-50:]


# ══════════════════════════════════════════════════════════════
# ⑧ 角色五：執行工程師
# ══════════════════════════════════════════════════════════════
class ExecutionEngineer:
    def __init__(self):
        self.orders: list = []
        self._api         = None

    def set_api(self, api):
        self._api = api

    def place(self, symbol: str, action: str, lots: int, price: float, reason: str) -> dict:
        oid = f"{'P' if PAPER_TRADE else 'R'}-{symbol}-{int(time.time())}"
        rec = dict(id=oid, symbol=symbol, action=action, lots=lots,
                   price=price, reason=reason,
                   status="simulated" if PAPER_TRADE else "sent",
                   time=datetime.now().strftime("%H:%M:%S"))
        self.orders.append(rec)
        log.info(f"{'📝[模擬]' if PAPER_TRADE else '✅[真實]'} {action} {symbol} {lots}張 @{price} | {reason}")

        if not PAPER_TRADE and self._api:
            try:
                import shioaji as sj
                from shioaji import constant
                contract = self._api.Contracts.Stocks[symbol]
                act = constant.Action.Buy if action == "Buy" else constant.Action.Sell
                order = self._api.Order(
                    price=price, quantity=lots, action=act,
                    price_type=constant.StockPriceType.LMT,
                    order_type=constant.OrderType.ROD,
                    order_lot=constant.StockOrderLot.Common,
                    account=self._api.stock_account,
                )
                trade = self._api.place_order(contract, order)
                rec["status"] = "placed"
                rec["broker_id"] = trade.order.id
            except Exception as e:
                rec["status"] = "error"
                rec["error"]  = str(e)
                Notifier.send("下單失敗", f"{symbol} {action} {lots}張\n錯誤：{e}", "alert")

        return rec

    def get_report(self) -> AgentReport:
        today  = [o for o in self.orders if o["time"] >= "09:00"]
        errors = [o for o in today if o.get("status") == "error"]
        status = "alert" if errors else "ok" if today else "idle"
        details = ([f"今日委託：{len(today)} 筆"] +
                   [f"{'❌' if o.get('status')=='error' else '✅'} {o['action']} {o['symbol']} {o['lots']}張 @{o['price']} {o['time']}"
                    for o in today[-6:]])
        return AgentReport("執行工程師", "⚙️", status, f"今日委託 {len(today)} 筆", details)


# ══════════════════════════════════════════════════════════════
# ⑨ 角色六：市場分析師
# ══════════════════════════════════════════════════════════════
class MarketAnalyst:
    def __init__(self):
        self.anomalies: list = []
        self._last_spike_key: dict[str, str] = {}
        self.current_regime: str = "neutral"  # bull / bear / neutral

    def analyze(self, symbol: str, bars: list, tick: dict, params: dict = None) -> AgentReport:
        if len(bars) < 5:
            return AgentReport("市場分析師", "🔭", "idle", "等待行情", ["等待 Tick…"])

        # 取得學習參數
        ap = params or {"regime_threshold": 1.5, "spike_sensitivity": 2.0}
        regime_th = ap.get("regime_threshold", 1.5)
        spike_sens = ap.get("spike_sensitivity", 2.0)

        closes = [b["close"] for b in bars]
        volumes = [b["volume"] for b in bars]
        price = tick.get("price", closes[-1])
        found = []

        if len(closes) >= 2:
            prev_close = closes[-2] or 1
            chg = (closes[-1] - prev_close) / prev_close * 100
            bar_time = str(bars[-1].get("time", datetime.now().strftime("%H:%M:%S")))
            spike_key = f"{symbol}:{bar_time}:{round(chg, 2)}"

            if abs(chg) > spike_sens:
                found.append(f"⚡ 單棒異常 {chg:+.1f}%")
                if self._last_spike_key.get(symbol) != spike_key:
                    self._last_spike_key[symbol] = spike_key
                    self.anomalies.append({
                        "symbol": symbol,
                        "type": "spike",
                        "val": round(chg, 2),
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "bar_time": bar_time,
                    })
                    self.anomalies = self.anomalies[-100:]

                if abs(chg) > 4:
                    Notifier.send(
                        f"異常波動 {symbol}",
                        f"單棒漲跌 {chg:+.1f}%，請注意風險",
                        "warn",
                        cooldown_key=f"market_spike:{symbol}",
                        cooldown_sec=300,
                    )

        avg_v = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else max(volumes[-1], 1)
        vr = volumes[-1] / (avg_v + 1)
        if vr > 3:
            found.append(f"💥 爆量 {vr:.1f}x")

        if len(bars) >= 6:
            if all(bars[-i-1]["close"] > bars[-i-1]["open"] for i in range(5)):
                found.append("📈 連續 5 紅棒，短線過熱")
            elif all(bars[-i-1]["close"] < bars[-i-1]["open"] for i in range(5)):
                found.append("📉 連續 5 綠棒，賣壓沉重")

        day_chg = (price - closes[0]) / (closes[0] or 1) * 100
        if not found:
            found.append(f"行情正常，今日 {day_chg:+.1f}%")
        found.insert(0, f"現價：{price:.2f}  今日 {day_chg:+.1f}%")

        # 判定市場 regime
        if day_chg > regime_th:
            self.current_regime = "bull"
        elif day_chg < -regime_th:
            self.current_regime = "bear"
        else:
            self.current_regime = "neutral"

        status = "warn" if any(k in " ".join(found) for k in ["異常", "爆量", "過熱", "沉重"]) else "ok"
        score = 50 + (day_chg * 5)  # 根據漲跌給分
        return AgentReport("市場分析師", "🔭", status, f"{symbol} {self.current_regime} 今日 {day_chg:+.1f}%", found, score=score)


# ══════════════════════════════════════════════════════════════
# ⑩ 模擬行情引擎（無 Shioaji 帳號時使用）
# ══════════════════════════════════════════════════════════════
class MockDataEngine:
    DEFAULT_BASES = {
        "2330":866,"2454":1265,"2382":267,"3017":588,"2317":154,"2308":342,
        "2603":80,"2881":75,"2882":60,"0050":150,"00679B":120,
    }
    DEFAULT_PRICE = 100

    def __init__(self, symbols=None):
        self.symbols = list(symbols or DETAIL_SYMBOLS)
        self.prices: dict[str, float] = {}
        self.last_quotes: dict[str, dict] = {}
        self.t       = 0
        self._t      = 0  # 總 tick 數（測試模式用）
        self.bars:   dict[str, deque] = {s: deque(maxlen=120) for s in self.symbols}
        self._buf:   dict[str, list]  = {s: [] for s in self.symbols}
        self._cmin:  dict[str, str]   = {}
        self._last_minute: str = ""
        self._finmind_cache: dict = {}
        self._all_stocks: list = []

    def load_all_stock_codes(self):
        """載入所有台灣股票代碼"""
        try:
            import twstock
            self._all_stocks = [c for c in twstock.codes.keys() if len(c) == 4 and c.isdigit()]
            log.info(f"已載入 {len(self._all_stocks)} 支股票代碼")
        except Exception as e:
            log.warning(f"載入股票代碼失敗：{e}")
            self._all_stocks = []

    def _fetch_finmind_latest(self, missing_symbols: list[str]) -> dict:
        """用 FinMind 補缺少的真實報價，不使用虛擬價格。"""
        token = os.getenv("FINMIND_TOKEN", "").strip()
        if not token or not missing_symbols:
            return {}

        url = "https://api.finmindtrade.com/api/v4/data"
        out = {}
        for sym in missing_symbols:
            for days_ago in range(0, 5):
                date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                params = {
                    "dataset": "TaiwanStockPrice",
                    "data_id": sym,
                    "start_date": date,
                    "end_date": date,
                    "token": token,
                }
                try:
                    resp = requests.get(url, params=params, timeout=15)
                    data = resp.json()
                except Exception as e:
                    log.warning(f"FinMind 查詢 {sym} 失敗：{e}")
                    break

                rows = data.get("data") or []
                if data.get("status") == 200 and rows:
                    row = rows[-1]
                    price = float(row.get("close", 0) or 0)
                    if price > 0:
                        out[sym] = {
                            "price": price,
                            "volume": int(row.get("Trading_Volume", 0) or 0),
                            "bid": None,
                            "ask": None,
                            "date": row.get("date", date),
                            "source": "finmind",
                        }
                        break
        if out:
            log.info(f"FinMind 補到 {len(out)} 支股票報價")
        return out

    def fetch_finmind_tick(self) -> dict:
        """真實報價來源：twstock 取得所有股票即時報價"""
        now_key = datetime.now().strftime("%Y-%m-%d %H:%M")
        if self._last_minute == now_key and self._finmind_cache:
            return self._finmind_cache
        
        self._last_minute = now_key
        result = {}
        
        # 載入所有股票代碼（如果還沒載入）
        if not self._all_stocks:
            self.load_all_stock_codes()
        
        if not self._all_stocks:
            log.warning("無股票代碼列表")
            return result
        
        # 使用 twstock 取得即時報價（分批每 10 支）
        try:
            import twstock
            # 只抓 WATCH_LIST 中的股票
            stocks_to_fetch = [s for s in self.symbols if s in WATCH_LIST]
            log.info(f"準備抓取股票: {stocks_to_fetch}")
            
            for i in range(0, len(stocks_to_fetch), 10):
                batch = stocks_to_fetch[i:i+10]
                try:
                    data = twstock.realtime.get(batch)
                    log.info(f"twstock 回應: {list(data.keys())}")
                    for sym, d in data.items():
                        if isinstance(d, dict) and d.get("success"):
                            rt = d.get("realtime", {})
                            price = rt.get("latest_trade_price", "")
                            vol = rt.get("trade_volume", "0")
                            if price and price not in ["-", "", None]:
                                result[sym] = {
                                    "price": float(price),
                                    "volume": int(vol or 0),
                                    "source": "twstock",
                                }
                                log.info(f"成功取得 {sym}: {price}")
                except Exception as e:
                    log.warning(f"twstock 批次 {i} 失敗：{e}")
            
            log.info(f"twstock 取得 {len(result)} 支股票即時報價")
        except Exception as e:
            log.warning(f"twstock 即時報價失敗：{e}")
        
        self._finmind_cache = result
        return result

    def _rnd(self, seed: int) -> float:
        return ((seed * 1664525 + 1013904223) & 0xFFFFFFFF) / 0xFFFFFFFF

    def tick(self) -> dict:
        self.t += 1
        if TEST_MODE:
            self._t += 1

        real_data = self.fetch_finmind_tick() or {}
        out = {}
        for sym in self.symbols:
            now_m = datetime.now().strftime("%H:%M")
            force_bar = TEST_MODE and self._t % 5 == 0

            if force_bar or (self._cmin.get(sym) and self._cmin[sym] != now_m):
                buf = self._buf[sym]
                if buf:
                    ps = [t["price"] for t in buf if t.get("price") is not None]
                    if ps:
                        self.bars[sym].append({
                            "time": self._cmin[sym], "open": ps[0],
                            "high": max(ps), "low": min(ps), "close": ps[-1],
                            "volume": sum(int(t.get("volume", 0) or 0) for t in buf),
                        })
                self._buf[sym] = []

            quote = real_data.get(sym)
            if quote and quote.get("price") is not None:
                price = float(quote["price"])
                bid = quote.get("bid")
                ask = quote.get("ask")
                tick = {
                    "price": price,
                    "volume": int(quote.get("volume", 0) or 0),
                    "bid": float(bid) if bid is not None else None,
                    "ask": float(ask) if ask is not None else None,
                    "bid_vol": 0,
                    "ask_vol": 0,
                    "available": True,
                    "stale": False,
                    "source": quote.get("source", "real"),
                    "quote_ts": time.time(),
                }
                self.prices[sym] = price
                self.last_quotes[sym] = tick.copy()
                self._buf[sym].append(tick)
                out[sym] = tick
            else:
                last = self.last_quotes.get(sym)
                if last and last.get("source") in {"twse", "finmind", "real"} and (time.time() - float(last.get("quote_ts", 0) or 0) <= REAL_QUOTE_CACHE_MAX_SEC):
                    tick = dict(last)
                    tick.update({"available": False, "stale": True, "source": "cached_real"})
                else:
                    tick = {
                        "price": None, "volume": 0, "bid": None, "ask": None,
                        "bid_vol": 0, "ask_vol": 0, "available": False,
                        "stale": True, "source": "unavailable",
                        "quote_ts": None,
                    }
                out[sym] = tick

            self._cmin[sym] = now_m
        return out

    # ══ 歷史資料載入 ══
    def load_csv(self, symbol: str, csv_path: str = None) -> bool:
        """從 CSV 載入歷史 K 棒資料"""
        if csv_path is None:
            csv_path = f"data/{symbol}.csv"
        
        if not os.path.exists(csv_path):
            log.warning(f"找不到歷史資料：{csv_path}")
            # 嘗試從公開資料庫下載
            return self.download_from_finmind(symbol)
        
        try:
            df = pd.read_csv(csv_path)
            required = ['date', 'open', 'high', 'low', 'close', 'volume']
            if not all(c in df.columns for c in required):
                log.warning(f"CSV 缺少必要欄位：{required}")
                return False
            
            bars = []
            for _, row in df.iterrows():
                bars.append({
                    "time": str(row['date']),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": int(row['volume']),
                })
            
            self.bars[symbol] = deque(bars[-120:], maxlen=120)
            if bars:
                last_close = float(bars[-1]["close"])
                self.prices[symbol] = last_close
            log.info(f"✅ 載入歷史資料 {symbol}：{len(bars)} 根 K 棒")
            return True
        except Exception as e:
            log.error(f"載入歷史資料失敗：{e}")
            return False

    def download_from_finmind(self, symbol: str) -> bool:
        """從 FinMind API 下載歷史資料"""
        token = os.getenv("FINMIND_TOKEN", "")
        if not token:
            log.info("無 FINMIND_TOKEN，無法下載歷史資料")
            return False
        
        try:
            url = "https://api.finmindtrade.com/api/v4/data"
            params = {
                "dataset": "TaiwanStockPrice",
                "data_id": symbol,
                "start_date": (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
                "token": token,
            }
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data.get("status") == 200 and data.get("data"):
                rows = data["data"]
                bars = []
                for r in rows:
                    bars.append({
                        "time": r.get("date", ""),
                        "open": float(r.get("open", 0)),
                        "high": float(r.get("max", 0)),
                        "low": float(r.get("min", 0)),
                        "close": float(r.get("close", 0)),
                        "volume": int(r.get("Trading_Volume", 0)),
                    })
                
                if bars:
                    self.bars[symbol] = deque(bars[-120:], maxlen=120)
                    last_close = float(bars[-1]["close"])
                    self.prices[symbol] = last_close
                    log.info(f"✅ 下載 {symbol} 歷史：{len(bars)} 根 K 棒")
                    return True
        except Exception as e:
            log.warning(f"FinMind 下載失敗：{e}")
        return False

    def load_all_historical(self):
        """載入所有監控股票的歷史資料"""
        for sym in self.symbols:
            self.load_csv(sym)
            # 如果沒有資料，嘗試下載
            if not self.bars[sym]:
                self.download_from_finmind(sym)


# ══════════════════════════════════════════════════════════════
# ⑪ 主交易引擎
# ══════════════════════════════════════════════════════════════
class TradingEngine:
    def __init__(self):
        self.detail_symbols = DETAIL_SYMBOLS[:]
        self.quant      = QuantResearcher()
        self.backtester = Backtester()
        self.risk       = RiskOfficer()
        self.signal_eng = SignalEngineer()
        self.execution  = ExecutionEngineer()
        self.analyst    = MarketAnalyst()
        self.mock       = MockDataEngine(self.detail_symbols)

        self.latest_ticks:   dict = {}
        self.agent_reports:  dict = {}
        self.backtest_cache: dict = {}
        self.trades_log:     list[TradeRecord] = []
        self._api                 = None
        self._running             = False
        self._trading_active      = False   # 只在盤中時間交易
        self._latest_decision_ids: dict = {}  # 記住每檔股票的決策 ID

        self.names = dict(SYM_NAMES)
        self.universe_rows = TaiwanMarketUniverse.load() if SCAN_ALL_TW else [{"symbol": s, "name": SYM_NAMES.get(s, s), "market": "tse"} for s in self.detail_symbols]
        for row in self.universe_rows:
            self.names[row["symbol"]] = row.get("name", row["symbol"])
        self.market_scanner = MarketScanner(self.universe_rows) if SCAN_ALL_TW else None
        self.market_board: list[dict] = []
        self._scan_task = None
        self._scan_last_request = 0.0

    def refresh_market_scan(self):
        if not self.market_scanner:
            self.market_board = []
            return []
        board = self.market_scanner.refresh()
        self.market_board = board
        for row in board:
            self.names[row["symbol"]] = row.get("name", row["symbol"])
        return board

    # ── Shioaji 連線 ──
    def connect_shioaji(self):
        if PAPER_TRADE:
            log.info("📝 紙交易模式")
            return
        try:
            import shioaji as sj
            api = sj.Shioaji()
            api.login(api_key=os.getenv("SHIOAJI_API_KEY",""),
                      secret_key=os.getenv("SHIOAJI_SECRET_KEY",""),
                      fetch_contract=True)
            api.activate_ca(ca_path=os.getenv("SHIOAJI_CERT_PATH",""),
                            ca_passwd=os.getenv("SHIOAJI_CERT_PASS",""),
                            person_id=os.getenv("SHIOAJI_ACCOUNT_ID",""))
            self._api = api
            self.execution.set_api(api)
            log.info("✅ Shioaji 連線成功")
            Notifier.send("系統啟動", "Shioaji 連線成功，交易引擎就緒", "info")
        except Exception as e:
            log.warning(f"Shioaji 失敗，使用模擬資料：{e}")

    # ── 主迴圈 ──
    async def run_loop(self):
        self._running = True
        log.info("🚀 交易引擎主迴圈啟動")
        bt_counter = 0

        while self._running:
            try:
                ticks = self.mock.tick()
                self.latest_ticks = ticks
                now_s = datetime.now().strftime("%H:%M")
                # 測試模式：無視時間限制，確保_auto_trade時會交易
                self._trading_active = AUTO_TRADE  # 移除時間限制，確保自動交易可運作
            except Exception as e:
                log.warning(f"⚠️ 取得報價失敗: {e}")
                await asyncio.sleep(TICK_INTERVAL)
                continue

            for sym in self.detail_symbols:
                try:
                    tick  = ticks[sym]
                    bars  = list(self.mock.bars[sym])
                    if tick.get("price") is None or tick.get("stale"):
                        self.agent_reports[f"market_{sym}"] = asdict(AgentReport("市場分析師", "🔭", "warn", f"{sym} 暫無最新真實報價", [f"資料來源：{tick.get('source','unavailable')}"]))
                        continue
                except Exception as e:
                    log.warning(f"⚠️ {sym} 處理異常: {e}")
                    continue

                try:
                    if bars:
                        self.signal_eng.update_vwap(sym, bars[-1])

                    obook = {"bid_vol": tick["bid_vol"], "ask_vol": tick["ask_vol"]}

                    # 取得 AI 學習參數
                    quant_params = learning_mgr.agent_memory.get("quant", {}).get("params", {})
                    backtest_params = learning_mgr.agent_memory.get("backtest", {}).get("params", {})
                    signal_params = learning_mgr.agent_memory.get("signal", {}).get("params", {})
                    risk_params = learning_mgr.agent_memory.get("risk", {}).get("params", {})
                    analyst_params = learning_mgr.agent_memory.get("analyst", {}).get("params", {})
                    
                    # 六角色分析
                    self.agent_reports[f"quant_{sym}"]    = asdict(self.quant.analyze(sym, bars, quant_params))
                    self.agent_reports[f"market_{sym}"]   = asdict(self.analyst.analyze(sym, bars, tick, analyst_params))
                    sig, sig_rep = self.signal_eng.evaluate(sym, bars, tick, obook, signal_params)
                    self.agent_reports[f"signal_{sym}"]   = asdict(sig_rep)
                except Exception as e:
                    log.warning(f"⚠️ {sym} 分析異常: {e}")
                    sig = None

                # 每 20 個 tick 跑一次回測（避免過度計算）
                if bt_counter % 20 == 0 and bars:
                    bt_rep, bt_res = self.backtester.run(sym, bars, backtest_params)
                    self.agent_reports[f"backtest_{sym}"] = asdict(bt_rep)
                    if bt_res:
                        self.backtest_cache[sym] = asdict(bt_res)

                # 信號 → 仲裁器 → 風控 → 下單
                if sig and self._trading_active:
                    # 收集各 AI 真實分數
                    quant_score = self.agent_reports.get(f"quant_{sym}", {}).get("score", 50)
                    backtest_score = self.agent_reports.get(f"backtest_{sym}", {}).get("score", 50)
                    analyst_score = self.agent_reports.get(f"market_{sym}", {}).get("score", 50)
                    
                    # risk 分數：根據風控狀態計算
                    remain = self.risk.MAX_DAILY_LOSS + self.risk.daily_pnl
                    if self.risk.is_halted:
                        risk_score = 0
                    elif remain < 500:
                        risk_score = 20
                    elif remain < 1500:
                        risk_score = 40
                    else:
                        risk_score = 80 - (self.risk.consecutive_loss * 15)
                    
                    # execution 分數：根據成交品質、流動性、滑價與學習參數計算
                    exec_params = learning_mgr.agent_memory.get("execution", {}).get("params", {})
                    slippage_th = exec_params.get("slippage_allow", 0.005)
                    liquidity_min = exec_params.get("liquidity_min", 1000)
                    fill_q = exec_params.get("fill_quality", 1.0)
                    
                    recent_orders = self.execution.orders[-10:]
                    recent_errors = [o for o in recent_orders if o.get("status") == "error"]
                    
                    # 基礎分數
                    if len(recent_orders) == 0:
                        base_score = 70
                    elif len(recent_errors) > 3:
                        base_score = 20
                    elif len(recent_errors) > 0:
                        base_score = 50
                    else:
                        base_score = 75
                    
                    # 根據 slippage_allow 調整：進場價與現價差異大則扣分
                    price = tick.get("price", 0)
                    entry_estimate = price
                    slippage_pct = abs(price - entry_estimate) / price if price > 0 else 0
                    if slippage_pct > slippage_th:
                        base_score -= 20
                    
                    # 根據 liquidity_min 調整：成交量不足則扣分
                    vol = tick.get("volume", 0)
                    if vol < liquidity_min:
                        base_score -= 15
                    
                    exec_score = max(0, base_score * fill_q)
                    
                    ai_scores = {
                        "quant": quant_score,
                        "backtest": backtest_score,
                        "risk": max(0, risk_score),
                        "signal": sig.confidence,
                        "execution": max(0, exec_score),
                        "analyst": analyst_score,
                    }
                    
                    # 仲裁器計算共識
                    regime = self.analyst.current_regime
                    consensus_score = learning_mgr.get_consensus_score(ai_scores, regime)
                    
                    # 共識門檻
                    CONSENSUS_THRESHOLD = 50
                    risk_ok, risk_reason = self.risk.can_enter(sig, tick["price"])
                    
                    # 仲裁決策：共識 + 風控 + execution 可交易性
                    exec_ok = exec_score >= 40
                    exec_reason = f"exec_score={exec_score:.0f}" if not exec_ok else "OK"
                    
                    if consensus_score >= CONSENSUS_THRESHOLD and risk_ok and exec_ok:
                        lots = self.risk.calc_lots(sig, tick["price"], risk_params)
                        if lots > 0:
                            act = "Buy" if sig.direction == Direction.LONG else "Sell"
                            self.execution.place(sym, act, lots, tick["price"], sig.reason)
                            self.risk.on_entry(sig, lots, tick["price"], ai_scores, regime)
                            log.info(f"✅ 仲裁通過 {sym} {sig.direction} {lots}張 @{tick['price']} 共識{consensus_score:.0f}%")
                            
                            # 記錄完整決策（包含六 AI 各自 judgment/confidence/reason）
                            decision_id = f"D{int(time.time()*1000)}"
                            quant_rep = self.agent_reports.get(f"quant_{sym}", {})
                            backtest_rep = self.agent_reports.get(f"backtest_{sym}", {})
                            signal_rep = self.agent_reports.get(f"signal_{sym}", {})
                            risk_report = self.risk.get_report()
                            
                            learning_mgr.log_decision({
                                "id": decision_id,
                                "symbol": sym,
                                "action": act,
                                "price": tick["price"],
                                "volume": tick.get("volume", 0),
                                "reason": sig.reason,
                                "ai_source": sig.ai_source,
                                "ai_scores": ai_scores,
                                "consensus_score": consensus_score,
                                "regime": regime,
                                "final_decision": "進場",
                                "entry_price": tick["price"],
                                "stop_loss": sig.stop_loss,
                                "target": sig.target_1,
                                "ai_judgments": {
                                    "quant": {"judgment": "buy" if quant_score >= 50 else "sell" if quant_score < 30 else "watch", "confidence": quant_score, "reason": quant_rep.get("summary", "")[:50]},
                                    "backtest": {"judgment": "buy" if backtest_score >= 55 else "sell" if backtest_score < 40 else "watch", "confidence": backtest_score, "reason": backtest_rep.get("summary", "")[:50]},
                                    "risk": {"judgment": "ok" if risk_score >= 60 else "halt" if risk_score < 20 else "caution", "confidence": risk_score, "reason": risk_reason[:50] if risk_reason else "OK"},
                                    "signal": {"judgment": str(sig.direction), "confidence": sig.confidence, "reason": sig.reason[:50]},
                                    "execution": {"judgment": "ok" if exec_score >= 60 else "risk" if exec_score < 40 else "caution", "confidence": exec_score, "reason": f"{len(recent_errors)} errors" if recent_errors else "healthy"},
                                    "analyst": {"judgment": regime, "confidence": analyst_score, "reason": f"{regime} regime"},
                                },
                            })
                            
                            self._latest_decision_ids[sym] = decision_id
                            
                            Notifier.send(
                                f"進場信號 {sym}",
                                f"方向：{'多頭' if sig.direction==Direction.LONG else '空頭'}\n"
                                f"共識：{consensus_score:.0f}% | 信心度：{sig.confidence:.0f}%\n"
                                f"進場：{tick['price']} | 止損：{sig.stop_loss}",
                                "info",
                            )
                    else:
                        # 記錄不進場原因（先取得各 AI 報告）
                        decision_id = f"D{int(time.time()*1000)}"
                        quant_rep = self.agent_reports.get(f"quant_{sym}", {})
                        backtest_rep = self.agent_reports.get(f"backtest_{sym}", {})
                        learning_mgr.log_decision({
                            "id": decision_id,
                            "symbol": sym,
                            "action": None,
                            "price": tick["price"],
                            "reason": f"共識{consensus_score:.0f}%<{CONSENSUS_THRESHOLD} 或 {risk_reason}",
                            "ai_source": sig.ai_source,
                            "ai_scores": ai_scores,
                            "consensus_score": consensus_score,
                            "regime": regime,
                            "final_decision": "不進場",
                            "ai_judgments": {
                                "quant": {"judgment": "buy" if quant_score >= 50 else "sell" if quant_score < 30 else "watch", "confidence": quant_score, "reason": quant_rep.get("summary", "")[:50]},
                                "backtest": {"judgment": "buy" if backtest_score >= 55 else "sell" if backtest_score < 40 else "watch", "confidence": backtest_score, "reason": backtest_rep.get("summary", "")[:50]},
                                "risk": {"judgment": "halt" if risk_score < 20 else "caution", "confidence": risk_score, "reason": risk_reason[:50] if risk_reason else "OK"},
                                "signal": {"judgment": str(sig.direction), "confidence": sig.confidence, "reason": sig.reason[:50]},
                                "execution": {"judgment": "risk" if exec_score < 40 else "caution", "confidence": exec_score, "reason": f"{len(recent_errors)} errors" if recent_errors else "healthy"},
                                "analyst": {"judgment": regime, "confidence": analyst_score, "reason": f"{regime} regime"},
                            },
                        })
                        log.debug(f"⛔ 仲裁攔截 {sym}：共識{consensus_score:.0f}% 風險:{risk_reason}")
                    if not risk_ok:
                        log.debug(f"⛔ 風控攔截 {sym}：{risk_reason}")

                # 持倉管理
                self._manage_positions(sym, tick["price"])

            # 全市場掃描（背景執行，避免主迴圈被大量 HTTP 阻塞）
            try:
                if self.market_scanner:
                    now_ts = time.time()
                    if (self._scan_task is None or self._scan_task.done()) and now_ts - self._scan_last_request >= SCAN_REFRESH_SEC:
                        self._scan_last_request = now_ts
                        self._scan_task = asyncio.create_task(asyncio.to_thread(self.refresh_market_scan))

                # 公用 agent 報告
                self.agent_reports["risk"]      = asdict(self.risk.get_report())
                self.agent_reports["execution"] = asdict(self.execution.get_report())
                bt_counter += 1
            except Exception as e:
                log.warning(f"⚠️ 主迴圈單筆異常: {type(e).__name__}: {e}")
            
            await asyncio.sleep(TICK_INTERVAL)

    # ── 持倉管理 ──
    def _manage_positions(self, symbol: str, price: float):
        pos = self.risk.open_positions.get(symbol)
        if not pos:
            return

        now = datetime.now().strftime("%H:%M")
        entry = pos["entry"]
        mult = 1 if pos["direction"] == Direction.LONG else -1
        act = "Sell" if pos["direction"] == Direction.LONG else "Buy"
        
        # 追蹤浮盈浮虧
        unrealized = (price - entry) * mult
        pos.setdefault("max_favorable", 0)
        pos.setdefault("max_adverse", 0)
        if unrealized > pos["max_favorable"]:
            pos["max_favorable"] = unrealized
        if unrealized < pos["max_adverse"]:
            pos["max_adverse"] = unrealized

        def close(reason: str):
            current_pos = self.risk.open_positions.get(symbol)
            if not current_pos:
                return
            lots = current_pos["lots"]
            pnl = (price - entry) * mult * lots * 1000 * 0.9985
            self.execution.place(symbol, act, lots, price, reason)
            self.risk.on_exit(symbol, pnl)
            self.trades_log.append(TradeRecord(
                id=f"T{int(time.time())}", symbol=symbol,
                direction=str(pos["direction"]), entry=entry, exit=price,
                lots=lots, pnl=round(pnl, 0), reason=reason,
                open_time="", close_time=now,
            ))
            
            # 記錄完整結果到學習系統
            decision_id = self._latest_decision_ids.get(symbol)
            if decision_id:
                entry_time_str = pos.get("entry_time", "")
                hold_duration = 0
                if entry_time_str:
                    try:
                        entry_dt = datetime.strptime(entry_time_str, "%Y-%m-%d %H:%M:%S")
                        exit_dt = datetime.now()
                        hold_duration = int((exit_dt - entry_dt).total_seconds() / 60)
                    except:
                        hold_duration = 0
                
                max_favorable = pos.get("max_favorable", 0)
                max_adverse = pos.get("max_adverse", 0)
                
                # error classification
                if "停損" in reason:
                    error_type = "stop_loss"
                elif "強制" in reason:
                    error_type = "time_exit"
                elif "目標" in reason:
                    error_type = "take_profit"
                elif pnl < 0:
                    error_type = "negative_pnl"
                else:
                    error_type = "take_profit"
                
                learning_mgr.log_outcome({
                    "id": decision_id,
                    "symbol": symbol,
                    "entry": entry,
                    "exit": price,
                    "pnl": pnl,
                    "reason": reason,
                    "success": pnl > 0,
                    "hold_duration": hold_duration,
                    "max_favorable": max_favorable,
                    "max_adverse": max_adverse,
                    "error_type": error_type,
                    "ai_scores": pos.get("ai_scores", {}),
                    "regime": pos.get("regime", "neutral"),
                })
                del self._latest_decision_ids[symbol]
            
            Notifier.send(
                f"出場 {symbol}",
                f"原因：{reason}\n進場：{entry:.2f} → 出場：{price:.2f}\n"
                f"損益：NT$ {pnl:+.0f}（今日累計 NT$ {self.risk.daily_pnl:+.0f}）",
                "ok" if pnl >= 0 else "warn",
                cooldown_key=f"exit:{symbol}:{reason}:{now}",
                cooldown_sec=0,
            )

        if now >= self.risk.FORCE_CLOSE:
            close("強制平倉")
            return
        if mult * (price - pos["stop"]) < 0:
            close("停損")
            return
        if mult * (price - pos["t2"]) > 0:
            close("目標獲利")
            return

        profit_pct = ((price - entry) / entry) * mult if entry else 0
        if profit_pct > 0.01:
            new_stop = entry + (0.005 * mult * entry)
            if mult * (new_stop - pos["stop"]) > 0:
                pos["stop"] = new_stop
                log.info(f"移動停損更新 {symbol}: {new_stop:.2f}")

        if mult * (price - pos["t1"]) > 0 and not pos["partial"]:
            half = max(1, pos["lots"] // 2)
            self.execution.place(symbol, act, half, price, "部分獲利")
            pos["lots"] -= half
            pos["partial"] = True

    # ── 狀態快照 ──
    def get_state(self) -> dict:
        return {
            "ticks":          self.latest_ticks,
            "agents":         self.agent_reports,
            "positions":      self.risk.open_positions,
            "daily_pnl":      self.risk.daily_pnl,
            "daily_trades":   self.risk.daily_trades,
            "is_halted":      self.risk.is_halted,
            "halt_reason":    self.risk.halt_reason,
            "trading_active": self._trading_active,
            "auto_trade":     AUTO_TRADE,
            "paper_trade":    PAPER_TRADE,
            "trades_log":     [asdict(t) for t in self.trades_log[-30:]],
            "backtest":       self.backtest_cache,
            "signal_history": self.signal_eng.get_history(),
            "anomalies":      self.analyst.anomalies[-20:],
            "market_board":   self.market_board,
            "detail_symbols": self.detail_symbols,
            "names":          self.names,
            "universe_size":  len(self.universe_rows),
            "scan_all_tw":    bool(self.market_scanner),
            "timestamp":      datetime.now().strftime("%H:%M:%S"),
        }


# ══════════════════════════════════════════════════════════════
# ⑫ 排程：每天自動重置
# ══════════════════════════════════════════════════════════════
engine = TradingEngine()

def daily_open():
    """09:00 自動執行：重置風控、重置 VWAP、發通知"""
    log.info("🌅 每日開盤重置")
    engine.risk.reset_daily()
    for sym in engine.detail_symbols:
        engine.signal_eng.reset_vwap(sym)

def daily_close():
    """13:30 自動執行：強制平倉、發收盤報告"""
    log.info("🌇 收盤強制平倉")
    for sym, pos in list(engine.risk.open_positions.items()):
        tick = engine.latest_ticks.get(sym)
        if tick:
            act = "Sell" if pos["direction"] == Direction.LONG else "Buy"
            engine._manage_positions(sym, tick["price"])
    Notifier.send(
        "每日交收報告",
        f"今日損益：NT$ {engine.risk.daily_pnl:+.0f}\n"
        f"交易次數：{engine.risk.daily_trades}\n"
        f"系統狀態：{'停機' if engine.risk.is_halted else '正常'}",
        "info",
    )

def _schedule_thread():
    if schedule is None:
        log.warning("未安裝 schedule，已停用自動排程；可手動使用重置/強制平倉功能")
        return
    schedule.every().day.at("09:00").do(daily_open)
    schedule.every().day.at("13:30").do(daily_close)
    while True:
        schedule.run_pending()
        time.sleep(30)

threading.Thread(target=_schedule_thread, daemon=True).start()


# ══════════════════════════════════════════════════════════════
# ⑬ FastAPI
# ══════════════════════════════════════════════════════════════
app = FastAPI(title="台股 AI 六角色交易系統")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

clients: list[WebSocket] = []

@app.on_event("startup")
async def startup():
    engine.connect_shioaji()
    # 嘗試載入歷史資料
    log.info("📊 檢查歷史資料...")
    engine.mock.load_all_historical()
    if engine.market_scanner:
        log.info(f"🌐 全市場掃描已啟用，股票池 {len(engine.universe_rows)} 檔，前端顯示前 {MARKET_BOARD_LIMIT} 檔")
        await asyncio.to_thread(engine.refresh_market_scan)
    
    asyncio.create_task(engine.run_loop())
    asyncio.create_task(_broadcast_loop())
    log.info("🚀 FastAPI 啟動完成，WebSocket 埠 8765")

async def _broadcast_loop():
    while True:
        if clients:
            state = engine.get_state()
            msg   = json.dumps(state, ensure_ascii=False, default=str)
            dead  = []
            for ws in clients:
                try:
                    await ws.send_text(msg)
                except:
                    dead.append(ws)
            for ws in dead:
                clients.remove(ws)
        await asyncio.sleep(BROADCAST_INTERVAL)

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    log.info(f"🔌 前端連線，共 {len(clients)} 個 | IP: {ws.client}")
    
    # 追蹤此連線的心跳
    ws._last_heartbeat = time.time()
    ws._alive = True
    
    try:
        await ws.send_text(json.dumps(engine.get_state(), ensure_ascii=False, default=str))

        while True:
            try:
                # 心跳超時 60 秒視為斷線
                raw = await asyncio.wait_for(ws.receive_text(), timeout=60)
            except asyncio.TimeoutError:
                # 檢查最後心跳時間
                last_hb = getattr(ws, '_last_heartbeat', time.time())
                if time.time() - last_hb > 60:
                    log.info(f"🔌 前端心跳逾時，断開 | IP: {ws.client}")
                    break
                continue  # 還活著，繼續等

            # 更新心跳時間
            ws._last_heartbeat = time.time()

            try:
                cmd = json.loads(raw)
            except json.JSONDecodeError:
                log.debug(f"忽略無效訊息：{raw[:80]}")
                continue

            action = cmd.get("cmd")
            if action in {"ping", "heartbeat"}:
                ws._last_heartbeat = time.time()  # 更新心跳
                continue
            if action == "reset":
                daily_open()
                log.info("指令：重置每日統計")
            elif action == "force_close":
                daily_close()
                log.info("指令：強制平倉")
            elif action == "notify_test":
                Notifier.send("測試通知", "Line/Email 通知測試成功 ✅", "info", cooldown_sec=0)
                log.info("指令：測試通知")
            elif action == "toggle_auto":
                global AUTO_TRADE
                AUTO_TRADE = not AUTO_TRADE
                log.info(f"指令：自動交易切換為 {AUTO_TRADE}")
                await ws.send_json({"type": "settings_updated", "auto_trade": AUTO_TRADE})
    except WebSocketDisconnect:
        log.info(f"🔌 前端斷線，剩 {len(clients)-1} 個 | IP: {ws.client}")
    except Exception as e:
        log.warning(f"🔌 WebSocket 異常: {type(e).__name__}: {e}")
    finally:
        if ws in clients:
            clients.remove(ws)

# REST API（給外部呼叫或除錯用）
@app.get("/api/state")
def api_state():
    return engine.get_state()

@app.get("/api/backtest/{symbol}")
def api_backtest(symbol: str):
    return engine.backtest_cache.get(symbol, {"error": "尚無回測資料"})

@app.get("/api/trades")
def api_trades():
    return [asdict(t) for t in engine.trades_log]

@app.get("/api/signals")
def api_signals():
    return engine.signal_eng.get_history()

@app.post("/api/toggle_mode")
def api_toggle_mode():
    global PAPER_TRADE
    PAPER_TRADE = not PAPER_TRADE
    mode = "紙交易" if PAPER_TRADE else "真實交易"
    log.info(f"交易模式切換：{mode}")
    return {"mode": mode, "paper_trade": PAPER_TRADE}

@app.get("/api/mode")
def api_mode():
    return {"mode": "紙交易" if PAPER_TRADE else "真實交易", "paper_trade": PAPER_TRADE, "auto_trade": AUTO_TRADE}

@app.get("/api/search")
def api_search(q: str = ""):
    """股票搜尋 API"""
    if not q or len(q) < 1:
        return []
    
    import twstock
    results = []
    q_upper = q.upper()
    for code, info in twstock.codes.items():
        if len(code) == 4 and code.isdigit():
            name = info.name if hasattr(info, 'name') else str(info)
            if q_upper in code or q_upper in name.upper():
                results.append({"code": code, "name": name})
                if len(results) >= 20:
                    break
    return results

@app.get("/api/settings")
def api_settings():
    """取得系統設定"""
    return {
        "paper_trade": PAPER_TRADE,
        "auto_trade": AUTO_TRADE,
        "total_capital": TOTAL_CAPITAL,
        "max_daily_loss": RiskOfficer.MAX_DAILY_LOSS,
        "max_single_loss": RiskOfficer.MAX_SINGLE_LOSS,
        "max_trades": RiskOfficer.MAX_TRADES,
        "max_positions": RiskOfficer.MAX_POSITIONS,
        "min_confidence": RiskOfficer.MIN_CONFIDENCE,
        "trade_start": RiskOfficer.TRADE_START,
        "trade_end": RiskOfficer.TRADE_END,
        "force_close": RiskOfficer.FORCE_CLOSE,
    }

@app.get("/api/learning")
def api_learning():
    """取得學習系統狀態"""
    return learning_mgr.get_status()

@app.post("/api/learning")
def api_learning_update(data: dict):
    """更新學習系統"""
    if "mode" in data:
        learning_mgr.set_mode(data["mode"])
    return {"status": "ok", "mode": learning_mgr.get_mode()}

@app.get("/api/learning/agents")
def api_learning_agents():
    """取得各 AI 權重"""
    return learning_mgr.get_agent_info()

@app.get("/api/learning/decisions")
def api_learning_decisions(limit: int = 20):
    """取得決策記錄"""
    return learning_mgr.decision_log[-limit:]

@app.get("/api/learning/outcomes")
def api_learning_outcomes(limit: int = 20):
    """取得結果記錄"""
    return learning_mgr.outcome_log[-limit:]

@app.post("/api/settings")
def api_update_settings(data: dict):
    """更新系統設定"""
    global PAPER_TRADE, AUTO_TRADE, TOTAL_CAPITAL
    
    if "paper_trade" in data:
        PAPER_TRADE = bool(data["paper_trade"])
    if "auto_trade" in data:
        global AUTO_TRADE
        AUTO_TRADE = bool(data["auto_trade"])
    if "total_capital" in data:
        TOTAL_CAPITAL = float(data["total_capital"])
    
    log.info(f"設定已更新：PAPER_TRADE={PAPER_TRADE}, AUTO_TRADE={AUTO_TRADE}, TOTAL_CAPITAL={TOTAL_CAPITAL}")
    return {"status": "ok", "paper_trade": PAPER_TRADE, "auto_trade": AUTO_TRADE}

@app.post("/api/test_trade")
def api_test_trade():
    """測試交易（模擬一筆交易）"""
    from datetime import datetime
    now = datetime.now().strftime("%H:%M:%S")
    
    # 模擬一筆交易
    test_trade = {
        "id": f"TEST-{int(time.time())}",
        "symbol": "2330",
        "action": "Buy",
        "lots": 1,
        "price": 2000.0,
        "reason": "測試交易",
        "status": "simulated",
        "time": now,
        "logic": "這是測試交易邏輯記錄",
    }
    
    engine.trades_log.append(test_trade)
    log.info(f"[測試交易] 買入 2330 1張 @ 2000")
    
    return test_trade

@app.post("/api/stop_robot")
def api_stop_robot():
    """立即停止自動交易"""
    global AUTO_TRADE
    AUTO_TRADE = False
    log.info("🤖 自動交易已強制停止")
    return {"status": "ok", "auto_trade": False}

@app.get("/api/backtest_dates")
def api_backtest_dates():
    """取得可回測的日期列表"""
    import os
    from datetime import datetime, timedelta
    
    dates = []
    for i in range(1, 31):  # 最近30天
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        dates.append(d)
    return dates

@app.get("/api/simulate/{date}")
def api_simulate(date: str):
    """模擬指定日期的交易"""
    log.info(f"📊 模擬交易 {date}")
    
    # 讀取當日歷史資料
    results = {}
    for sym in engine.detail_symbols:
        csv_path = f"data/{sym}.csv"
        if not os.path.exists(csv_path):
            continue
        
        try:
            df = pd.read_csv(csv_path)
            df['date'] = pd.to_datetime(df['date']).dt.strftime("%Y-%m-%d")
            day_df = df[df['date'] == date]
            
            if day_df.empty:
                continue
            
            # 簡單模擬：根據開盤/收盤買賣
            bars = []
            for _, row in day_df.iterrows():
                bars.append({
                    "time": str(row['date']) + " " + str(row.get('time', '')),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": int(row['volume']),
                })
            
            if len(bars) >= 5:
                entry_price = bars[0]['open']
                exit_price = bars[-1]['close']
                pnl = (exit_price - entry_price) * 1000  # 1張 = 1000股
                results[sym] = {
                    "entry": entry_price,
                    "exit": exit_price,
                    "pnl": pnl,
                    "bars": len(bars),
                }
        except Exception as e:
            log.warning(f"模擬 {sym} 失敗：{e}")
    
    log.info(f"模擬完成：{len(results)} 筆交易")
    return results

@app.get("/api/simdata/{date}")
def api_simdata(date: str, symbol: str = None):
    """取得模擬所需的歷史資料 - 使用記憶體中的資料"""
    import random
    
    # 股票報價對照
    BASE_PRICES = {
        "2330": 2000, "2454": 1265, "2382": 267, "3017": 588,
        "2317": 154, "2308": 342, "2603": 80, "2881": 75,
        "2882": 60, "0050": 150,
    }
    
    # 決定用哪個股票
    target = symbol or list(BASE_PRICES.keys())[0]
    base_price = BASE_PRICES.get(target, 1000)
    
    # 產生 60 根 K 棒的隨機走勢
    all_bars = []
    change_pct = 0
    for i in range(60):
        change_pct += random.uniform(-0.025, 0.025)
        close = base_price * (1 + change_pct)
        o = base_price * (1 + change_pct * random.uniform(-0.5, 0.5))
        h = max(o, close) + random.uniform(0, base_price * 0.01)
        l = min(o, close) - random.uniform(0, base_price * 0.01)
        all_bars.append({
            "time": f"第{i+1}根",
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(close, 2),
            "volume": random.randint(1000, 10000),
        })
        base_price = close
    
    log.info(f"[模擬資料] {target} {len(all_bars)} 根K棒")
    return {"symbol": target, "bars": all_bars}

@app.get("/api/universe")
def api_universe():
    return {
        "scan_all_tw": bool(engine.market_scanner),
        "universe_size": len(engine.universe_rows),
        "detail_symbols": engine.detail_symbols,
        "display_limit": MARKET_BOARD_LIMIT,
    }

@app.get("/api/health")
def api_health():
    return {
        "ok": True,
        "paper_trade": PAPER_TRADE,
        "trading_active": engine._trading_active,
        "clients": len(clients),
        "time": datetime.now().strftime("%H:%M:%S"),
    }

from fastapi import UploadFile, File

@app.post("/api/upload/{symbol}")
async def upload_history(symbol: str, file: UploadFile = File(...)):
    """上傳 CSV 歷史資料"""
    os.makedirs("data", exist_ok=True)
    path = f"data/{symbol}.csv"
    
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    
    # 重新載入
    ok = engine.mock.load_csv(symbol, path)
    return {"ok": ok, "symbol": symbol, "bars": len(engine.mock.bars.get(symbol, []))}

from fastapi.responses import FileResponse, Response

@app.get("/")
def read_root():
    return FileResponse("index_v2.html", media_type="text/html")

@app.get("/favicon.ico")
def favicon():
    return Response(b"", media_type="image/x-icon")


if __name__ == "__main__":
    print("=" * 60)
    print("  台股 AI 六角色自動交易系統 v2.0")
    print("  模式：" + ("PAPER (紙交易)" if PAPER_TRADE else "LIVE (真實交易)"))
    print("  精選池：" + ", ".join(DETAIL_SYMBOLS))
    print(f"  全市場掃描：{'ON' if SCAN_ALL_TW else 'OFF'} | 股票池 {len(engine.universe_rows)} 檔 | 顯示前 {MARKET_BOARD_LIMIT} 檔")
    print("  自動排程：" + ("ON" if AUTO_TRADE else "OFF"))
    print("  Line 通知：" + ("ON" if LINE_TOKEN else "OFF"))
    print("  Email 通知：" + ("ON" if EMAIL_FROM else "OFF"))
    print("  前端：直接開啟 index_v2.html")
    print("=" * 60)
    uvicorn.run("server_v2:app", host="0.0.0.0", port=8765, reload=False)
