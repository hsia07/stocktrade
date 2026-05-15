from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


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
    summary: str = ""

    @property
    def decision_changed(self) -> bool:
        return self.decision_before != self.decision_after

    @property
    def changed_field_count(self) -> int:
        return sum(1 for f in self.fields if f.changed)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DecisionComparator:
    def compare(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
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

        decision_before = before.get("final_decision", "")
        decision_after = after.get("final_decision", "")
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
