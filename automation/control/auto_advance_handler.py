"""
BLOCKER_H: Telegram / API handler for auto-advance dispatch.

Entry point for external triggers (Telegram bot, REST API, cron, etc.)
to safely dispatch the next round.

Flow:
1. Accept a round_result dict (from whatever source)
2. Verify auto_candidate_ready + automated_signoff + can_dispatch_next_round
3. If all pass, call dispatch_next_round to create candidate scaffold
4. Never merge, push, promote, or create a PR directly
5. Return structured result indicating what was done (scaffold only)
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from automation.control.auto_advance import AutoAdvanceController

logger = logging.getLogger("auto_advance_handler")


def handle_auto_advance_trigger(
    round_result: Dict[str, Any],
    *,
    controller: AutoAdvanceController | None = None,
) -> Dict[str, Any]:
    """
    Process an auto-advance trigger from Telegram / API / cron.

    Accepts a round_result and:

    1. Checks can_dispatch_next_round (which internally checks:
       - is_new_round_dispatch / status == completed
       - formal_status_code == auto_candidate_ready
       - no blockers, evidence complete, not paused
       - automated signoff verified
       - next round is determinable)
    2. If dispatchable, creates the next-round candidate scaffold
    3. Never merges, pushes, promotes, or creates a PR

    Args:
        round_result: dict with round_id, status, formal_status_code,
                      automated_signoff, and other round metadata.
        controller: optional AutoAdvanceController instance; created
                    fresh if not provided.

    Returns:
        dict with dispatch outcome including safety flags.
    """
    ctrl = controller or AutoAdvanceController()

    can_dispatch, reason, detail = ctrl.can_dispatch_next_round(round_result)
    if not can_dispatch:
        return {
            "handled": True,
            "trigger_accepted": False,
            "reason": reason,
            "detail": detail,
            "dispatch_executed": False,
            "scaffold_created": False,
            "scaffold_path": None,
            "next_round_id": None,
            "merge_executed": False,
            "push_executed": False,
            "promote_executed": False,
            "pr_created": False,
        }

    dispatch = ctrl.dispatch_next_round(round_result)

    return {
        "handled": True,
        "trigger_accepted": True,
        "reason": dispatch.get("reason", ""),
        "detail": dispatch.get("detail", ""),
        "dispatch_executed": dispatch.get("dispatch_executed", False),
        "scaffold_created": dispatch.get("scaffold_created", False),
        "scaffold_path": dispatch.get("scaffold_path"),
        "next_round_id": dispatch.get("next_round_id"),
        "merge_executed": False,
        "push_executed": False,
        "promote_executed": False,
        "pr_created": False,
    }
