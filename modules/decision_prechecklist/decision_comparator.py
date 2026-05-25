from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from .replay_trace import DiffReasonCode


@dataclass
class ComparisonFieldDiff:
    field_name: str
    before_value: Any
    after_value: Any
    changed: bool


@dataclass
class DecisionComparisonReport:
    trace_id_before: str
    trace_id_after: str
    symbol: str
    side: str
    decision_before: str
    decision_after: str
    fields: list[ComparisonFieldDiff] = field(default_factory=list)
    step_diffs: list[dict[str, Any]] = field(default_factory=list)
    veto_diffs: list[dict[str, Any]] = field(default_factory=list)
    market_reality_diffs: list[dict[str, Any]] = field(default_factory=list)
    confidence_diffs: list[dict[str, Any]] = field(default_factory=list)
    diff_reason_codes: list[str] = field(default_factory=list)
    as_of_validation: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    @property
    def decision_changed(self) -> bool:
        return self.decision_before != self.decision_after

    @property
    def changed_field_count(self) -> int:
        return sum(1 for f in self.fields if f.changed)

    @property
    def has_as_of_violation(self) -> bool:
        return self.as_of_validation.get("violation", False)

    @property
    def has_future_leak(self) -> bool:
        return self.as_of_validation.get("future_leak", False)

    @property
    def has_veto_replay_mismatch(self) -> bool:
        return any(c.startswith("veto_ignored") or c == "veto_ignored_in_replay"
                   for c in self.diff_reason_codes)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DecisionComparator:
    def compare(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
        market_reality_before: dict[str, Any] | None = None,
        market_reality_after: dict[str, Any] | None = None,
        confidence_before: dict[str, Any] | None = None,
        confidence_after: dict[str, Any] | None = None,
        as_of_before: dict[str, Any] | None = None,
        as_of_after: dict[str, Any] | None = None,
    ) -> DecisionComparisonReport:
        trace_id_before = before.get("trace_id", "")
        trace_id_after = after.get("trace_id", "")
        symbol = before.get("symbol", after.get("symbol", ""))
        side = before.get("side", after.get("side", ""))

        scalar_fields = [
            "symbol", "side", "candidate_action", "final_decision",
            "order_ref", "fill_ref", "pnl_ref",
            "chain_link_id", "previous_trace_hash",
        ]
        fields: list[ComparisonFieldDiff] = []
        for fname in scalar_fields:
            bv = before.get(fname, None)
            av = after.get(fname, None)
            fields.append(ComparisonFieldDiff(
                field_name=fname,
                before_value=bv,
                after_value=av,
                changed=bv != av,
            ))

        step_diffs = self._compare_steps(
            before.get("decision_chain", []),
            after.get("decision_chain", []),
        )

        veto_diffs = self._compare_any(
            before.get("vetoes", []),
            after.get("vetoes", []),
        )

        market_reality_diffs = self._compare_market_reality(
            market_reality_before or {},
            market_reality_after or {},
        )

        confidence_diffs = self._compare_confidence_labels(
            confidence_before or {},
            confidence_after or {},
        )

        decision_before = before.get("final_decision", "")
        decision_after = after.get("final_decision", "")
        reason_codes: list[str] = []
        self._collect_reason_codes(
            reason_codes, fields, step_diffs, veto_diffs,
            market_reality_diffs, confidence_diffs,
            before, after, decision_before, decision_after,
        )

        as_of_result = self._check_as_of_guard(as_of_before or {}, as_of_after or {})
        if as_of_result.get("violation"):
            code = DiffReasonCode.DECISION_TS_BEFORE_TRADABLE_TS.value
            if code not in reason_codes:
                reason_codes.append(code)
        if as_of_result.get("future_leak"):
            code = DiffReasonCode.FUTURE_LEAK_DETECTED.value
            if code not in reason_codes:
                reason_codes.append(code)

        changed_count = sum(1 for f in fields if f.changed)
        summary_parts = []
        if decision_before != decision_after:
            summary_parts.append(
                f"decision changed: {decision_before} -> {decision_after}"
            )
        if changed_count:
            summary_parts.append(f"{changed_count} field(s) changed")
        if step_diffs:
            summary_parts.append(f"{len(step_diffs)} step difference(s)")
        if veto_diffs:
            summary_parts.append(f"{len(veto_diffs)} veto difference(s)")
        if market_reality_diffs:
            summary_parts.append(f"{len(market_reality_diffs)} market reality diff(s)")
        if confidence_diffs:
            summary_parts.append(f"{len(confidence_diffs)} confidence diff(s)")
        if as_of_result.get("violation"):
            summary_parts.append(f"as-of violation: {as_of_result.get('reason', '')}")
        if as_of_result.get("future_leak"):
            summary_parts.append("future leak detected")
        if reason_codes:
            summary_parts.append(f"reason codes: {','.join(reason_codes)}")
        summary = "; ".join(summary_parts) if summary_parts else "no differences"

        return DecisionComparisonReport(
            trace_id_before=trace_id_before,
            trace_id_after=trace_id_after,
            symbol=symbol,
            side=side,
            decision_before=decision_before,
            decision_after=decision_after,
            fields=fields,
            step_diffs=step_diffs,
            veto_diffs=veto_diffs,
            market_reality_diffs=market_reality_diffs,
            confidence_diffs=confidence_diffs,
            diff_reason_codes=reason_codes,
            as_of_validation=as_of_result,
            summary=summary,
        )

    def compare_from_traces(
        self,
        before_trace: Any,
        after_trace: Any,
    ) -> DecisionComparisonReport:
        before_dict = before_trace.to_dict() if hasattr(before_trace, "to_dict") else {}
        after_dict = after_trace.to_dict() if hasattr(after_trace, "to_dict") else {}
        return self.compare(before_dict, after_dict)

    def _compare_steps(
        self,
        before_steps: list[Any],
        after_steps: list[Any],
    ) -> list[dict[str, Any]]:
        before_map = {s.get("step_name", ""): s for s in self._normalize_steps(before_steps)}
        after_map = {s.get("step_name", ""): s for s in self._normalize_steps(after_steps)}
        all_keys = set(before_map.keys()) | set(after_map.keys())
        diffs: list[dict[str, Any]] = []
        for key in sorted(all_keys):
            b = before_map.get(key)
            a_obj = after_map.get(key)
            if b is None:
                diffs.append({"step": key, "type": "added", "before": None, "after": a_obj})
            elif a_obj is None:
                diffs.append({"step": key, "type": "removed", "before": b, "after": None})
            elif b.get("result") != a_obj.get("result") or b.get("detail") != a_obj.get("detail"):
                diffs.append({"step": key, "type": "changed", "before": b, "after": a_obj})
        return diffs

    def _compare_any(
        self,
        before_list: list[Any],
        after_list: list[Any],
    ) -> list[dict[str, Any]]:
        def _key(item: Any) -> str:
            if isinstance(item, dict):
                return item.get("gate", item.get("reason_code", ""))
            return str(item)

        before_map = {_key(x): x for x in before_list}
        after_map = {_key(x): x for x in after_list}
        all_keys = set(before_map.keys()) | set(after_map.keys())
        diffs: list[dict[str, Any]] = []
        for key in sorted(all_keys):
            b = before_map.get(key)
            a_obj = after_map.get(key)
            if b is None:
                diffs.append({"key": key, "type": "added", "before": None, "after": a_obj})
            elif a_obj is None:
                diffs.append({"key": key, "type": "removed", "before": b, "after": None})
            elif b != a_obj:
                diffs.append({"key": key, "type": "changed", "before": b, "after": a_obj})
        return diffs

    @staticmethod
    def _normalize_steps(steps: list[Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for s in steps:
            if isinstance(s, dict):
                result.append(s)
            elif hasattr(s, "step_name"):
                result.append(asdict(s))
            else:
                result.append({"step_name": str(s), "result": "", "detail": ""})
        return result

    def _compare_market_reality(
        self,
        before_mr: dict[str, Any],
        after_mr: dict[str, Any],
    ) -> list[dict[str, Any]]:
        diffs: list[dict[str, Any]] = []
        all_keys = set(before_mr.keys()) | set(after_mr.keys())
        for key in sorted(all_keys):
            bv = before_mr.get(key)
            av = after_mr.get(key)
            if bv != av:
                diffs.append({
                    "field": key,
                    "before": bv,
                    "after": av,
                })
        return diffs

    def _compare_confidence_labels(
        self,
        before_conf: dict[str, Any],
        after_conf: dict[str, Any],
    ) -> list[dict[str, Any]]:
        diffs: list[dict[str, Any]] = []
        all_keys = set(before_conf.keys()) | set(after_conf.keys())
        for key in sorted(all_keys):
            bv = before_conf.get(key)
            av = after_conf.get(key)
            if bv != av:
                diffs.append({
                    "label": key,
                    "before": bv,
                    "after": av,
                })
        return diffs

    @staticmethod
    def _check_as_of_guard(
        as_of_before: dict[str, Any],
        as_of_after: dict[str, Any],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "violation": False,
            "future_leak": False,
            "reason": "",
            "details": {},
        }
        before_ts = as_of_before.get("decision_ts", "")
        after_ts = as_of_after.get("decision_ts", "")
        before_tradable = as_of_before.get("tradable_ts", "")
        after_tradable = as_of_after.get("tradable_ts", "")

        def _parse_ts(ts_str: str) -> datetime | None:
            if not ts_str:
                return None
            try:
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                return datetime.fromisoformat(ts_str)
            except (ValueError, TypeError):
                return None

        dt_before = _parse_ts(before_ts)
        dt_after = _parse_ts(after_ts)
        dt_before_tradable = _parse_ts(before_tradable)
        dt_after_tradable = _parse_ts(after_tradable)

        if dt_before and dt_before_tradable and dt_before < dt_before_tradable:
            result["violation"] = True
            result["reason"] = f"decision_ts {before_ts} before tradable_ts {before_tradable}"
            result["details"] = {
                "decision_ts": before_ts,
                "tradable_ts": before_tradable,
                "type": "before_replay_decision_ts_before_tradable_ts",
            }

        if dt_after and dt_after_tradable and dt_after < dt_after_tradable:
            result["violation"] = True
            result["reason"] = f"replayed decision_ts {after_ts} before tradable_ts {after_tradable}"
            result["details"] = {
                "decision_ts": after_ts,
                "tradable_ts": after_tradable,
                "type": "after_replay_decision_ts_before_tradable_ts",
            }

        source_ts = as_of_before.get("source_ts", "")
        publish_ts = as_of_before.get("publish_ts", "")
        ingest_ts = as_of_before.get("ingest_ts", "")
        dt_source = _parse_ts(source_ts)
        dt_publish = _parse_ts(publish_ts)
        dt_ingest = _parse_ts(ingest_ts)
        if dt_before and dt_source and dt_source > dt_before:
            result["future_leak"] = True
            result["reason"] = f"source_ts {source_ts} after decision_ts {before_ts}"
        if dt_before and dt_publish and dt_publish > dt_before:
            result["future_leak"] = True
            result["reason"] = f"publish_ts {publish_ts} after decision_ts {before_ts}"
        if dt_before and dt_ingest and dt_ingest > dt_before:
            result["future_leak"] = True
            result["reason"] = f"ingest_ts {ingest_ts} after decision_ts {before_ts}"

        return result

    @staticmethod
    def _collect_reason_codes(
        reason_codes: list[str],
        fields: list[ComparisonFieldDiff],
        step_diffs: list[dict[str, Any]],
        veto_diffs: list[dict[str, Any]],
        market_reality_diffs: list[dict[str, Any]],
        confidence_diffs: list[dict[str, Any]],
        before: dict[str, Any],
        after: dict[str, Any],
        decision_before: str,
        decision_after: str,
    ) -> None:
        if not before.get("trace_id"):
            reason_codes.append(DiffReasonCode.MISSING_TRACE_ID.value)
        if not after.get("trace_id"):
            reason_codes.append(DiffReasonCode.MISSING_TRACE_ID.value)
        if not before.get("final_decision"):
            reason_codes.append(DiffReasonCode.MISSING_FINAL_DECISION.value)
        if not after.get("final_decision"):
            reason_codes.append(DiffReasonCode.MISSING_FINAL_DECISION.value)
        if decision_before != decision_after:
            reason_codes.append(DiffReasonCode.DECISION_CHANGED.value)
        for f in fields:
            if f.changed:
                reason_codes.append(f"{DiffReasonCode.FIELD_CHANGED.value}:{f.field_name}")
        for sd in step_diffs:
            stype = sd.get("type", "changed")
            if stype == "added":
                reason_codes.append(f"{DiffReasonCode.STEP_ADDED.value}:{sd.get('step','')}")
            elif stype == "removed":
                reason_codes.append(f"{DiffReasonCode.STEP_REMOVED.value}:{sd.get('step','')}")
            else:
                reason_codes.append(f"{DiffReasonCode.STEP_CHANGED.value}:{sd.get('step','')}")
        for vd in veto_diffs:
            vtype = vd.get("type", "changed")
            key = vd.get("key", "unknown")
            if vtype == "added" and vd.get("after", {}).get("gate", "") != "original_veto":
                reason_codes.append(f"{DiffReasonCode.VETO_ADDED_IN_REPLAY.value}:{key}")
            elif vtype == "removed":
                reason_codes.append(f"{DiffReasonCode.VETO_REMOVED_IN_REPLAY.value}:{key}")
        for mrd in market_reality_diffs:
            reason_codes.append(f"{DiffReasonCode.MARKET_REALITY_SNAPSHOT_CHANGED.value}:{mrd.get('field','')}")
        for cd in confidence_diffs:
            reason_codes.append(f"{DiffReasonCode.CONFIDENCE_CALIBRATION_CHANGED.value}:{cd.get('label','')}")

    def build_replay_result(
        self,
        report: DecisionComparisonReport,
        audit_record_dict: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = {
            "trace_id": report.trace_id_before or report.trace_id_after,
            "original_record_hash": (audit_record_dict or {}).get("record_hash", ""),
            "replay_version": "r033-v1",
            "replay_timestamp": datetime.now(timezone.utc).isoformat(),
            "original_decision": report.decision_before,
            "replayed_decision": report.decision_after,
            "diff_summary": report.summary,
            "diff_reason_codes": report.diff_reason_codes,
            "has_veto_replay_mismatch": report.has_veto_replay_mismatch,
            "has_as_of_violation": report.has_as_of_violation,
            "has_future_leak": report.has_future_leak,
            "confidence_labels": {
                "raw": "unavailable",
                "calibrated": "unavailable",
            },
            "market_reality_snapshot": (audit_record_dict or {}).get("market_reality", {}),
            "taiwan_constraints": (audit_record_dict or {}).get("taiwan_constraints", {}),
            "as_of_fields": report.as_of_validation.get("details", {}),
            "previous_replay_hash": "",
            "chain_link_id": "",
        }
        return result
