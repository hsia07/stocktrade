"""
Mode Transition Recorder for Audit Trails
Round 8: State Machine and Mode Switching Governance
"""
import json
from datetime import datetime


class ModeRecorder:
    """Records all mode transitions for audit and compliance"""
    
    def __init__(self):
        self.transition_history = []
    
    def record_transition(self, from_mode: str, to_mode: str, operator: str, reason: str):
        """
        Record a mode transition with timestamp and metadata
        
        Args:
            from_mode: Source mode
            to_mode: Target mode
            operator: Who/what initiated the transition
            reason: Why the transition occurred
        """
        transition = {
            'timestamp': datetime.now().isoformat(),
            'from_mode': from_mode,
            'to_mode': to_mode,
            'operator': operator,
            'reason': reason
        }
        self.transition_history.append(transition)
    
    def get_transition_history(self):
        """Get complete list of all recorded transitions"""
        return self.transition_history
    
    def get_last_transition(self):
        """Get the most recent transition, or None if no history"""
        if not self.transition_history:
            return None
        return self.transition_history[-1]
    
    def get_transitions_by_mode(self, mode: str):
        """
        Get all transitions involving a specific mode
        
        Args:
            mode: Mode name to filter by
            
        Returns:
            List of transitions where mode appears as from_mode or to_mode
        """
        return [
            t for t in self.transition_history 
            if t['from_mode'] == mode or t['to_mode'] == mode
        ]
    
    def export_to_json(self, file_path: str):
        """
        Export transition history to JSON file for evidence preservation
        
        Args:
            file_path: Path to output JSON file
        """
        with open(file_path, 'w') as f:
            json.dump(self.transition_history, f, indent=4)
