import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mobile_emergency_takeover import MobileEmergencyTakeoverConfig, get_default_config


def test_mobile_layout_metadata_exists():
    config = get_default_config()
    assert hasattr(config, 'mobile_friendly_layout_metadata')
    assert isinstance(config.mobile_friendly_layout_metadata, dict)
    assert 'viewport_width_range' in config.mobile_friendly_layout_metadata


def test_emergency_takeover_entry_exists():
    config = get_default_config()
    assert hasattr(config, 'emergency_takeover_entry_state')
    assert isinstance(config.emergency_takeover_entry_state, dict)
    assert 'enabled' in config.emergency_takeover_entry_state


def test_emergency_pause_descriptor_exists():
    config = get_default_config()
    assert hasattr(config, 'emergency_pause_action_descriptor')
    assert isinstance(config.emergency_pause_action_descriptor, dict)
    assert 'action' in config.emergency_pause_action_descriptor


def test_takeover_status_payload_exists():
    config = get_default_config()
    assert hasattr(config, 'takeover_status_card_payload')
    assert isinstance(config.takeover_status_card_payload, dict)
    assert 'status' in config.takeover_status_card_payload


def test_touch_target_min_size():
    config = get_default_config()
    assert config.touch_target_metadata['min_size_px'] >= 44


def test_operator_confirmation_required():
    config = get_default_config()
    assert config.operator_confirmation_required is True


def test_safe_mode_banner_exists():
    config = get_default_config()
    assert hasattr(config, 'safe_mode_banner_payload')
    assert isinstance(config.safe_mode_banner_payload, dict)
    assert 'message' in config.safe_mode_banner_payload


def test_no_server_v2_dependency():
    import mobile_emergency_takeover as mod
    source = open(mod.__file__, 'r', encoding='utf-8').read()
    assert 'server_v2' not in source


def test_no_index_v2_dependency():
    import mobile_emergency_takeover as mod
    source = open(mod.__file__, 'r', encoding='utf-8').read()
    assert 'index_v2' not in source


def test_no_r024_files_dependency():
    import mobile_emergency_takeover as mod
    source = open(mod.__file__, 'r', encoding='utf-8').read()
    assert 'smart_summary_layer' not in source
    assert 'R024-SMART-SUMMARY-LAYER' not in source


def test_accessibility_metadata_present():
    config = get_default_config()
    assert hasattr(config, 'accessibility_metadata')
    assert config.accessibility_metadata.get('aria_labels') is True


def test_narrow_screen_layout_present():
    config = get_default_config()
    assert hasattr(config, 'narrow_screen_safe_layout_metadata')
    assert 'max_width' in config.narrow_screen_safe_layout_metadata
