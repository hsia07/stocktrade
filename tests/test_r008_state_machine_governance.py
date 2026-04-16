"""
Round 8 Tests: State Machine and Mode Switching Governance
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime

from governance.state_machine.mode_controller import ModeController, Mode
from governance.state_machine.mode_recorder import ModeRecorder


class TestModeController:
    """Test mode controller functionality"""
    
    def test_controller_initialization(self):
        """ModeController initializes with correct transition rules"""
        controller = ModeController()
        
        assert Mode.OBSERVE in controller.allowed_transitions
        assert Mode.SIM in controller.allowed_transitions
        assert len(controller.allowed_transitions) == 6  # All 6 modes
    
    def test_validate_valid_transition(self):
        """Valid transitions are accepted"""
        controller = ModeController()
        
        # Test OBSERVE -> SIM
        valid, reason = controller.validate_transition(Mode.OBSERVE, Mode.SIM)
        assert valid == True
        assert "allowed" in reason.lower()
    
    def test_validate_invalid_transition(self):
        """Invalid transitions are rejected"""
        controller = ModeController()
        
        # Test LIVE -> SIM (should not be allowed directly)
        valid, reason = controller.validate_transition(Mode.LIVE, Mode.SIM)
        assert valid == False
        assert "not allowed" in reason.lower()
    
    def test_get_allowed_transitions(self):
        """Returns correct list of allowed next modes"""
        controller = ModeController()
        
        allowed = controller.get_allowed_transitions(Mode.OBSERVE)
        assert Mode.SIM in allowed
        assert Mode.SHADOW in allowed
        assert Mode.PAUSE in allowed
        assert Mode.LIVE not in allowed  # Cannot go directly to LIVE from OBSERVE
    
    def test_transition_requires_approval(self):
        """High-risk transitions require approval"""
        controller = ModeController()
        
        # SIM -> LIVE should require approval
        assert controller.transition_requires_approval(Mode.SIM, Mode.LIVE) == True
        
        # SIM -> OBSERVE should not require approval
        assert controller.transition_requires_approval(Mode.SIM, Mode.OBSERVE) == False
    
    def test_get_mode_description(self):
        """Returns human-readable description"""
        controller = ModeController()
        
        desc = controller.get_mode_description(Mode.LIVE)
        assert "live" in desc.lower() or "trading" in desc.lower()
        
        desc = controller.get_mode_description(Mode.PAUSE)
        assert "pause" in desc.lower() or "stop" in desc.lower()
    
    def test_get_transition_matrix(self):
        """Returns complete transition matrix"""
        controller = ModeController()
        
        matrix = controller.get_transition_matrix()
        assert "observe" in matrix
        assert "sim" in matrix
        assert "live" in matrix
        assert "allowed" in matrix["observe"]
        assert "description" in matrix["observe"]


class TestModeRecorder:
    """Test mode transition recording"""
    
    def test_recorder_initialization(self):
        """ModeRecorder initializes with empty history"""
        recorder = ModeRecorder()
        
        assert recorder.transition_history == []
    
    def test_record_transition(self):
        """Transitions are recorded with all required fields"""
        recorder = ModeRecorder()
        
        recorder.record_transition(
            from_mode="OBSERVE",
            to_mode="SIM",
            operator="test_user",
            reason="Starting simulation"
        )
        
        assert len(recorder.transition_history) == 1
        assert recorder.transition_history[0]['from_mode'] == "OBSERVE"
        assert recorder.transition_history[0]['to_mode'] == "SIM"
        assert recorder.transition_history[0]['operator'] == "test_user"
        assert 'timestamp' in recorder.transition_history[0]
    
    def test_get_transition_history(self):
        """Returns complete transition history"""
        recorder = ModeRecorder()
        
        recorder.record_transition("OBSERVE", "SIM", "user1", "reason1")
        recorder.record_transition("SIM", "LIVE", "user2", "reason2")
        
        history = recorder.get_transition_history()
        assert len(history) == 2
        assert history[0]['from_mode'] == "OBSERVE"
        assert history[1]['from_mode'] == "SIM"
    
    def test_get_last_transition(self):
        """Returns most recent transition"""
        recorder = ModeRecorder()
        
        # Empty history should return None
        assert recorder.get_last_transition() is None
        
        recorder.record_transition("OBSERVE", "SIM", "user1", "reason1")
        recorder.record_transition("SIM", "LIVE", "user2", "reason2")
        
        last = recorder.get_last_transition()
        assert last['from_mode'] == "SIM"
        assert last['to_mode'] == "LIVE"
    
    def test_get_transitions_by_mode(self):
        """Filters transitions by mode"""
        recorder = ModeRecorder()
        
        recorder.record_transition("OBSERVE", "SIM", "user1", "reason1")
        recorder.record_transition("SIM", "LIVE", "user2", "reason2")
        recorder.record_transition("LIVE", "PAUSE", "user3", "reason3")
        
        # Get transitions involving SIM
        sim_transitions = recorder.get_transitions_by_mode("SIM")
        assert len(sim_transitions) == 2
    
    def test_export_to_json(self):
        """Exports history to JSON file"""
        import tempfile
        import json
        
        recorder = ModeRecorder()
        recorder.record_transition("OBSERVE", "SIM", "user1", "reason1")
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            recorder.export_to_json(temp_path)
            
            with open(temp_path, 'r') as f:
                loaded = json.load(f)
            
            assert len(loaded) == 1
            assert loaded[0]['from_mode'] == "OBSERVE"
        finally:
            os.unlink(temp_path)


class TestIntegration:
    """Test integration between controller and recorder"""
    
    def test_controller_with_recorder(self):
        """Controller validates, Recorder logs - workflow integration"""
        controller = ModeController()
        recorder = ModeRecorder()
        
        # Attempt transition
        from_mode = Mode.OBSERVE
        to_mode = Mode.SIM
        
        valid, reason = controller.validate_transition(from_mode, to_mode)
        
        if valid:
            # Record the transition
            requires_approval = controller.transition_requires_approval(from_mode, to_mode)
            approval_note = " (requires approval)" if requires_approval else ""
            
            recorder.record_transition(
                from_mode=from_mode.value,
                to_mode=to_mode.value,
                operator="system",
                reason=f"Valid transition{approval_note}"
            )
        
        # Verify
        assert valid == True
        assert len(recorder.transition_history) == 1
        assert recorder.transition_history[0]['from_mode'] == "observe"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
