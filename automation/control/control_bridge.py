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
LAST_ACTION_FILE = os.path.join(CONTROL_DIR, "last_action.runtime.json")
APPROVED_CANDIDATE_FILE = os.path.join(PROMOTION_DIR, "approved_candidate.runtime.json")
PROMOTION_PLAN_FILE = os.path.join(PROMOTION_DIR, "promotion_plan.runtime.json")
PROMOTION_RESULT_FILE = os.path.join(PROMOTION_DIR, "promotion_result.runtime.json")


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
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_POST(self):
        path = urlparse(self.path).path

        if path == '/approve-and-promote':
            result = do_approve_and_promote()
            self.send_json(200 if result['status'] == 'success' else 400, result)
        else:
            self.send_json(404, {'error': 'Not found'})


def main():
    host = '127.0.0.1'
    port = 8766

    server = HTTPServer((host, port), BridgeHandler)
    print(f"Control bridge listening on http://{host}:{port}")
    print("Endpoints:")
    print(f"  GET  http://{host}:{port}/ready")
    print(f"  GET  http://{host}:{port}/last-action")
    print(f"  POST http://{host}:{port}/approve-and-promote")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
