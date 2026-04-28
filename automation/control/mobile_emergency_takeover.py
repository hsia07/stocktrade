from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json


@dataclass
class MobileEmergencyTakeoverConfig:
    mobile_friendly_layout_metadata: Dict = field(default_factory=lambda: {
        "viewport_width_range": [320, 768],
        "font_size_min": 14,
        "button_height_min": 44,
        "spacing_min": 8
    })
    emergency_takeover_entry_state: Dict = field(default_factory=lambda: {
        "enabled": True,
        "trigger_conditions": ["manual_trigger", "auto_detect_mobile"],
        "state": "standby"
    })
    emergency_pause_action_descriptor: Dict = field(default_factory=lambda: {
        "action": "pause_all_trading",
        "confirmation_required": True,
        "timeout_seconds": 30
    })
    takeover_status_card_payload: Dict = field(default_factory=lambda: {
        "status": "active",
        "operator": None,
        "timestamp": None,
        "card_layout": "compact_mobile"
    })
    touch_target_metadata: Dict = field(default_factory=lambda: {
        "min_size_px": 44,
        "padding_px": 8,
        "target_type": "button"
    })
    accessibility_metadata: Dict = field(default_factory=lambda: {
        "aria_labels": True,
        "high_contrast": True,
        "screen_reader_friendly": True
    })
    narrow_screen_safe_layout_metadata: Dict = field(default_factory=lambda: {
        "max_width": 768,
        "stack_elements": True,
        "hide_non_essential": True
    })
    operator_confirmation_required: bool = True
    audit_log_descriptor: Dict = field(default_factory=lambda: {
        "log_events": ["takeover_start", "takeover_end", "pause_trigger"],
        "retention_days": 90,
        "log_level": "INFO"
    })
    safe_mode_banner_payload: Dict = field(default_factory=lambda: {
        "message": "Emergency Takeover Active - Mobile Mode",
        "banner_style": "warning",
        "dismissible": False
    })

    def to_dict(self) -> Dict:
        return {
            "mobile_friendly_layout_metadata": self.mobile_friendly_layout_metadata,
            "emergency_takeover_entry_state": self.emergency_takeover_entry_state,
            "emergency_pause_action_descriptor": self.emergency_pause_action_descriptor,
            "takeover_status_card_payload": self.takeover_status_card_payload,
            "touch_target_metadata": self.touch_target_metadata,
            "accessibility_metadata": self.accessibility_metadata,
            "narrow_screen_safe_layout_metadata": self.narrow_screen_safe_layout_metadata,
            "operator_confirmation_required": self.operator_confirmation_required,
            "audit_log_descriptor": self.audit_log_descriptor,
            "safe_mode_banner_payload": self.safe_mode_banner_payload
        }

    def save_side_channel(self, path: str = "automation/control/candidates/R025-MOBILE-EMERGENCY-TAKEOVER/takeover_runtime_state.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


def get_default_config() -> MobileEmergencyTakeoverConfig:
    return MobileEmergencyTakeoverConfig()
