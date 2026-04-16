"""
Mode Controller for Trading System Governance
Round 8: State Machine and Mode Switching Governance
"""
from enum import Enum


class Mode(Enum):
    """Trading system operational modes"""
    OBSERVE = "observe"      # Monitor only, no trades
    SIM = "sim"              # Simulation mode
    SHADOW = "shadow"        # Shadow trading mode
    LIVE = "live"            # Live trading mode
    PAUSE = "pause"          # Paused mode
    RECOVERY = "recovery"    # Recovery mode


class ModeController:
    """Controls and validates mode transitions"""
    
    def __init__(self):
        self.allowed_transitions = {
            Mode.OBSERVE: [Mode.SIM, Mode.SHADOW, Mode.PAUSE],
            Mode.SIM: [Mode.OBSERVE, Mode.SHADOW, Mode.LIVE, Mode.PAUSE],
            Mode.SHADOW: [Mode.OBSERVE, Mode.SIM, Mode.LIVE, Mode.PAUSE],
            Mode.LIVE: [Mode.PAUSE, Mode.RECOVERY],
            Mode.PAUSE: [Mode.OBSERVE, Mode.SIM, Mode.LIVE],
            Mode.RECOVERY: [Mode.PAUSE, Mode.OBSERVE]
        }
        
        self.high_risk_transitions = {
            (Mode.SIM, Mode.LIVE),
            (Mode.SHADOW, Mode.LIVE),
            (Mode.OBSERVE, Mode.LIVE),
            (Mode.LIVE, Mode.PAUSE),
            (Mode.LIVE, Mode.RECOVERY)
        }
        
        self.descriptions = {
            Mode.OBSERVE: "Monitor-only mode, observe market without trading",
            Mode.SIM: "Simulation mode, test strategies with simulated trades",
            Mode.SHADOW: "Shadow mode, execute strategy without real positions",
            Mode.LIVE: "Live trading mode, execute real trades with real capital",
            Mode.PAUSE: "Pause mode, stop all trading activities",
            Mode.RECOVERY: "Recovery mode, system recovering from errors"
        }
    
    def validate_transition(self, from_mode: Mode, to_mode: Mode) -> tuple[bool, str]:
        """
        Validate if mode transition is allowed
        
        Returns:
            (is_valid, reason)
        """
        if to_mode in self.allowed_transitions.get(from_mode, []):
            return True, "Transition allowed"
        else:
            allowed = [m.value for m in self.allowed_transitions.get(from_mode, [])]
            return False, f"Transition from {from_mode.value} to {to_mode.value} not allowed. Allowed: {allowed}"
    
    def get_allowed_transitions(self, current_mode: Mode) -> list[Mode]:
        """Get list of modes that can be transitioned to from current mode"""
        return self.allowed_transitions.get(current_mode, [])
    
    def transition_requires_approval(self, from_mode: Mode, to_mode: Mode) -> bool:
        """Check if transition requires manual approval"""
        return (from_mode, to_mode) in self.high_risk_transitions
    
    def get_mode_description(self, mode: Mode) -> str:
        """Get human-readable description of a mode"""
        return self.descriptions.get(mode, "Unknown mode")
    
    def get_transition_matrix(self) -> dict:
        """Get complete transition matrix for documentation"""
        matrix = {}
        for mode in Mode:
            matrix[mode.value] = {
                "allowed": [m.value for m in self.get_allowed_transitions(mode)],
                "description": self.get_mode_description(mode)
            }
        return matrix
