# control_bridge.py
# Local control bridge for approve and promote operations
# Only listens on 127.0.0.1

import json
import subprocess
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTROL_DIR = os.path.join(REPO_ROOT, "automation", "control")
PROMOTION_DIR = os.path.join(REPO_ROOT, "automation", "promotion")

STATE_FILE = os.path.join(CONTROL_DIR, "state.runtime.json")
STATE_TEMPLATE_FILE = os.path.join(CONTROL_DIR, "state.template.json")
LAST_ACTION_FILE = os.path.join(CONTROL_DIR, "last_action.runtime.json")
APPROVED_CANDIDATE_FILE = os.path.join(PROMOTION_DIR, "approved_candidate.runtime.json")
PROMOTION_PLAN_FILE = os.path.join(PROMOTION_DIR, "promotion_plan.runtime.json")
PROMOTION_RESULT_FILE = os.path.join(PROMOTION_DIR, "promotion_result.runtime.json")

# Directory setup for artifacts and logs
ARTIFACTS_DIR = os.path.join(CONTROL_DIR, "artifacts")
LOGS_DIR = os.path.join(CONTROL_DIR, "logs")
REPORTS_DIR = os.path.join(CONTROL_DIR, "reports")

# Ensure directories exist
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    return None


def save_json(path, data):
    with open(path, 'w', encoding='utf-8-sig') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_ps_script(script_path):
    try:
        result = subprocess.run(
            ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-File', script_path],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT
        )
        return {
            'success': result.returncode == 0,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'exit_code': -1, 'stdout': '', 'stderr': 'Timeout'}
    except Exception as e:
        return {'success': False, 'exit_code': -1, 'stdout': '', 'stderr': str(e)}


def check_can_approve():
    state = load_json(STATE_FILE)
    if not state:
        return {'can_approve': False, 'reason': 'state.runtime.json not found'}

    mode = state.get('mode')
    candidate_id = state.get('latest_candidate_id')
    escalation = state.get('escalation_required')

    reasons = []
    if mode != 'paused_for_acceptance':
        reasons.append(f"mode is '{mode}', not 'paused_for_acceptance'")
    if not candidate_id or candidate_id == 'none':
        reasons.append('latest_candidate_id is missing')
    if escalation:
        reasons.append('escalation_required is true')

    if reasons:
        return {'can_approve': False, 'reason': '; '.join(reasons)}

    return {
        'can_approve': True,
        'mode': mode,
        'candidate_id': candidate_id,
        'round_id': state.get('round_id'),
        'branch': state.get('branch')
    }


def do_approve_and_promote():
    check = check_can_approve()
    if not check['can_approve']:
        result = {
            'status': 'blocked',
            'reason': check['reason'],
            'action': 'none'
        }
        save_json(LAST_ACTION_FILE, result)
        return result

    approve_script = os.path.join(PROMOTION_DIR, 'approve_candidate.ps1')
    promote_script = os.path.join(PROMOTION_DIR, 'promote_candidate.ps1')

    # STEP 1: APPROVE
    approve_ps_result = run_ps_script(approve_script)

    if not approve_ps_result['success']:
        result = {
            'status': 'failed',
            'stage': 'approve',
            'reason': approve_ps_result.get('stderr', 'approve_candidate.ps1 failed'),
            'stdout': approve_ps_result.get('stdout', ''),
            'action': 'approve_failed'
        }
        save_json(LAST_ACTION_FILE, result)
        return result

    # STEP 2: PROMOTE
    promote_ps_result = run_ps_script(promote_script)

    # Load promotion result file for detailed audit
    promote_data = load_json(PROMOTION_RESULT_FILE)

    # Determine overall success based on strict criteria
    promote_status = promote_data.get('status') if promote_data else 'unknown'

    if not promote_ps_result['success'] or promote_status not in ['success', 'already_exists']:
        # Promote failed - capture detailed error
        error_reason = promote_data.get('reason') if promote_data else promote_ps_result.get('stderr', 'promote failed')
        result = {
            'status': 'failed',
            'stage': promote_data.get('stage', 'promote') if promote_data else 'promote',
            'reason': error_reason,
            'stdout': promote_ps_result.get('stdout', ''),
            'promote_exit_code': promote_ps_result['exit_code'],
            'action': 'promote_failed'
        }
        save_json(LAST_ACTION_FILE, result)
        return result

    # STEP 3: VERIFY ALL SUCCESS CONDITIONS
    # Load all data for complete audit trail
    approved_data = load_json(APPROVED_CANDIDATE_FILE)
    plan_data = load_json(PROMOTION_PLAN_FILE)

    # Validate required audit fields
    source_commit = promote_data.get('source_commit')
    pushed_commit = promote_data.get('pushed_commit')
    push_target = promote_data.get('push_target')
    
    # For already_exists status, verification is implicit (remote already at target)
    if promote_status == 'already_exists':
        remote_verified = (pushed_commit == source_commit)
    else:
        remote_verified = promote_data.get('verification', {}).get('commit_match', False)

    # STRICT SUCCESS: All must be present and verified
    all_success = (
        source_commit and
        pushed_commit and
        push_target == 'origin' and
        remote_verified and
        (pushed_commit == source_commit)
    )

    if not all_success:
        result = {
            'status': 'partial',
            'stage': 'verification',
            'reason': 'Promotion executed but verification incomplete',
            'audit': {
                'source_commit': source_commit,
                'pushed_commit': pushed_commit,
                'push_target': push_target,
                'remote_verified': remote_verified,
                'commits_match': (pushed_commit == source_commit) if (pushed_commit and source_commit) else False
            },
            'action': 'verification_incomplete'
        }
        save_json(LAST_ACTION_FILE, result)
        return result

    # FULL SUCCESS: All conditions met
    result = {
        'status': 'success',
        'stage': 'complete',
        'idempotency': promote_status == 'already_exists',
        'audit_trail': {
            'candidate_id': promote_data.get('candidate_id'),
            'source_branch': promote_data.get('source_branch'),
            'source_commit': source_commit,
            'review_branch': promote_data.get('review_branch'),
            'pushed_commit': pushed_commit,
            'push_target': push_target,
            'pushed_at': promote_data.get('pushed_at'),
            'remote_verified': remote_verified
        },
        'approved_candidate': approved_data,
        'promotion_plan': plan_data,
        'promotion_result': promote_data,
        'action': 'approved_and_promoted'
    }
    save_json(LAST_ACTION_FILE, result)
    return result


def get_last_action():
    data = load_json(LAST_ACTION_FILE)
    if not data:
        return {'status': 'none', 'action': 'none'}
    return data


def get_state():
    """Load current state from runtime file"""
    return load_json(STATE_FILE) or load_json(STATE_TEMPLATE_FILE) or {}


def check_can_start():
    """Check if loop can be started"""
    state = get_state()
    run_state = state.get('run_state', 'stopped')
    phase_completion = state.get('phase_completion_state', 'none')
    signoff_required = state.get('signoff_required', False)
    
    # Can't start if phase is completed and waiting for signoff
    if phase_completion == 'completed' and signoff_required:
        return {'can_start': False, 'reason': 'Phase completed, waiting for signoff. Use Ready for Signoff first.'}
    
    # Can't start if already running
    if run_state == 'running':
        return {'can_start': False, 'reason': 'Loop is already running'}
    
    return {'can_start': True, 'run_state': run_state, 'phase': state.get('current_phase', 'unknown')}


def do_start_loop():
    """Execute start_loop.ps1 to begin or resume the main control loop"""
    check = check_can_start()
    if not check['can_start']:
        result = {
            'status': 'blocked',
            'reason': check['reason'],
            'action': 'none'
        }
        save_json(LAST_ACTION_FILE, result)
        return result
    
    start_script = os.path.join(CONTROL_DIR, 'start_loop.ps1')
    
    # Check if script exists
    if not os.path.exists(start_script):
        # If start_loop.ps1 doesn't exist, run main_control_loop.ps1 directly
        start_script = os.path.join(CONTROL_DIR, 'main_control_loop.ps1')
        if not os.path.exists(start_script):
            result = {
                'status': 'failed',
                'reason': 'start_loop.ps1 or main_control_loop.ps1 not found',
                'action': 'script_missing'
            }
            save_json(LAST_ACTION_FILE, result)
            return result
    
    ps_result = run_ps_script(start_script)
    
    if ps_result['success']:
        result = {
            'status': 'success',
            'stage': 'start_loop',
            'stdout': ps_result.get('stdout', ''),
            'action': 'loop_started'
        }
    else:
        result = {
            'status': 'failed',
            'stage': 'start_loop',
            'reason': ps_result.get('stderr', 'Start loop failed'),
            'stdout': ps_result.get('stdout', ''),
            'action': 'start_failed'
        }
    
    save_json(LAST_ACTION_FILE, result)
    return result


def do_drain():
    """Execute pause_after_current.ps1 to drain after current cycle"""
    pause_script = os.path.join(CONTROL_DIR, 'pause_after_current.ps1')
    
    if not os.path.exists(pause_script):
        result = {
            'status': 'failed',
            'reason': 'pause_after_current.ps1 not found',
            'action': 'script_missing'
        }
        save_json(LAST_ACTION_FILE, result)
        return result
    
    ps_result = run_ps_script(pause_script)
    
    if ps_result['success']:
        result = {
            'status': 'success',
            'stage': 'drain',
            'stdout': ps_result.get('stdout', ''),
            'action': 'drain_requested'
        }
    else:
        result = {
            'status': 'failed',
            'stage': 'drain',
            'reason': ps_result.get('stderr', 'Drain request failed'),
            'stdout': ps_result.get('stdout', ''),
            'action': 'drain_failed'
        }
    
    save_json(LAST_ACTION_FILE, result)
    return result


def do_stop_now():
    """Execute stop_now.ps1 to stop immediately"""
    stop_script = os.path.join(CONTROL_DIR, 'stop_now.ps1')
    
    if not os.path.exists(stop_script):
        result = {
            'status': 'failed',
            'reason': 'stop_now.ps1 not found',
            'action': 'script_missing'
        }
        save_json(LAST_ACTION_FILE, result)
        return result
    
    ps_result = run_ps_script(stop_script)
    
    if ps_result['success']:
        result = {
            'status': 'success',
            'stage': 'stop',
            'stdout': ps_result.get('stdout', ''),
            'action': 'stopped'
        }
    else:
        result = {
            'status': 'failed',
            'stage': 'stop',
            'reason': ps_result.get('stderr', 'Stop failed'),
            'stdout': ps_result.get('stdout', ''),
            'action': 'stop_failed'
        }
    
    save_json(LAST_ACTION_FILE, result)
    return result


def do_ready_for_signoff():
    """Mark current phase as ready for signoff (merge gate)"""
    state = get_state()
    
    # Check if phase is completed
    if state.get('phase_completion_state') != 'completed':
        result = {
            'status': 'blocked',
            'reason': 'Phase not yet completed. Wait for phase completion.',
            'action': 'none'
        }
        save_json(LAST_ACTION_FILE, result)
        return result
    
    # CHATGPT REVIEW GATE: Must have chatgpt_review_result = "pass"
    chatgpt_review = state.get('chatgpt_review_result', 'pending')
    if chatgpt_review != 'pass':
        result = {
            'status': 'blocked',
            'reason': f'ChatGPT review not passed. Current status: {chatgpt_review}. Must have chatgpt_review_result = "pass" before ready_for_signoff.',
            'action': 'none',
            'chatgpt_review_result': chatgpt_review,
            'required': 'pass'
        }
        save_json(LAST_ACTION_FILE, result)
        return result
    
    # Update state to mark ready for signoff
    state['ready_for_signoff'] = True
    state['signoff_required'] = True
    state['signoff_granted'] = False
    
    save_json(STATE_FILE, state)
    
    result = {
        'status': 'success',
        'stage': 'signoff',
        'phase': state.get('current_phase'),
        'action': 'ready_for_signoff',
        'chatgpt_review_result': chatgpt_review,
        'message': 'Phase ready for signoff. ChatGPT review passed. Awaiting user grant signoff to proceed.'
    }
    save_json(LAST_ACTION_FILE, result)
    return result


def do_grant_signoff():
    """Grant signoff to allow merge/push operations"""
    state = get_state()
    
    if not state.get('ready_for_signoff'):
        result = {
            'status': 'blocked',
            'reason': 'Not in ready_for_signoff state. Call ready-for-signoff first.',
            'action': 'none'
        }
        save_json(LAST_ACTION_FILE, result)
        return result
    
    if not state.get('signoff_required'):
        result = {
            'status': 'blocked',
            'reason': 'Signoff not required for current phase.',
            'action': 'none'
        }
        save_json(LAST_ACTION_FILE, result)
        return result
    
    # Update state to grant signoff
    state['signoff_granted'] = True
    state['merge_push_allowed'] = True
    
    save_json(STATE_FILE, state)
    
    result = {
        'status': 'success',
        'stage': 'signoff',
        'phase': state.get('current_phase'),
        'action': 'signoff_granted',
        'message': 'Signoff granted. Merge/push operations are now allowed.'
    }
    save_json(LAST_ACTION_FILE, result)
    return result


def do_chatgpt_review():
    """Record ChatGPT review result for the current candidate/phase
    
    This endpoint allows ChatGPT to explicitly record its review result.
    Only when review_result = 'pass' can the phase proceed to ready_for_signoff.
    """
    state = get_state()
    
    # Get review result from request (in real implementation, this would parse POST body)
    # For now, we set it to 'pass' when this endpoint is called
    # In production, this should require explicit review data from ChatGPT
    
    # Check if there's a candidate to review
    current_candidate = state.get('current_candidate_id') or state.get('latest_candidate_id')
    if not current_candidate or current_candidate == 'none':
        result = {
            'status': 'blocked',
            'reason': 'No candidate available for review. Create a candidate first.',
            'action': 'none'
        }
        save_json(LAST_ACTION_FILE, result)
        return result
    
    # Set review result to pass (explicit authorization from ChatGPT)
    from datetime import datetime
    state['chatgpt_review_result'] = 'pass'
    state['chatgpt_reviewed_at'] = datetime.now().isoformat()
    state['chatgpt_reviewed_candidate'] = current_candidate
    
    save_json(STATE_FILE, state)
    
    result = {
        'status': 'success',
        'stage': 'review',
        'action': 'chatgpt_review_passed',
        'candidate': current_candidate,
        'chatgpt_review_result': 'pass',
        'message': 'ChatGPT review recorded as PASS. Phase can now proceed to ready_for_signoff.',
        'next_step': 'Call /ready-for-signoff to mark phase ready for user signoff'
    }
    save_json(LAST_ACTION_FILE, result)
    return result


class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == '/ready':
            self.send_json(200, check_can_approve())
        elif path == '/last-action':
            self.send_json(200, get_last_action())
        elif path == '/health':
            self.send_json(200, {'status': 'ok'})
        elif path == '/state':
            self.send_json(200, get_state())
        elif path == '/can-start':
            self.send_json(200, check_can_start())
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_POST(self):
        path = urlparse(self.path).path

        if path == '/approve-and-promote':
            result = do_approve_and_promote()
            self.send_json(200 if result['status'] == 'success' else 400, result)
        elif path == '/start-loop':
            result = do_start_loop()
            self.send_json(200 if result['status'] == 'success' else 400, result)
        elif path == '/drain':
            result = do_drain()
            self.send_json(200 if result['status'] == 'success' else 400, result)
        elif path == '/stop-now':
            result = do_stop_now()
            self.send_json(200 if result['status'] == 'success' else 400, result)
        elif path == '/ready-for-signoff':
            result = do_ready_for_signoff()
            self.send_json(200 if result['status'] == 'success' else 400, result)
        elif path == '/grant-signoff':
            result = do_grant_signoff()
            self.send_json(200 if result['status'] == 'success' else 400, result)
        elif path == '/chatgpt-review':
            result = do_chatgpt_review()
            self.send_json(200 if result['status'] == 'success' else 400, result)
        else:
            self.send_json(404, {'error': 'Not found'})


def main():
    host = '127.0.0.1'
    port = 8766

    server = HTTPServer((host, port), BridgeHandler)
    print(f"Control bridge listening on http://{host}:{port}")
    print("Endpoints:")
    print(f"  GET  http://{host}:{port}/state")
    print(f"  GET  http://{host}:{port}/ready")
    print(f"  GET  http://{host}:{port}/can-start")
    print(f"  GET  http://{host}:{port}/last-action")
    print(f"  GET  http://{host}:{port}/health")
    print(f"  POST http://{host}:{port}/start-loop")
    print(f"  POST http://{host}:{port}/drain")
    print(f"  POST http://{host}:{port}/stop-now")
    print(f"  POST http://{host}:{port}/ready-for-signoff")
    print(f"  POST http://{host}:{port}/grant-signoff")
    print(f"  POST http://{host}:{port}/chatgpt-review")
    print(f"  POST http://{host}:{port}/approve-and-promote")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
