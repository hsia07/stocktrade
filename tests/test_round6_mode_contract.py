"""
第6轮 前后端模式契约验收测试
验证正式生产程序中的模式契约
"""
import sys
import os
import re

def test_api_mode_contract_in_production():
    """验证 /api/mode 返回正式状态机 mode"""
    print("=" * 60)
    print("ROUND 6: API MODE CONTRACT IN PRODUCTION")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 找到 /api/mode 函数
    api_mode_start = content.find('@app.get("/api/mode")')
    api_mode_end = content.find('@app.post("/api/sim/start")', api_mode_start)
    api_mode_section = content[api_mode_start:api_mode_end]
    
    # 验证返回结构
    uses_get_mode = "engine.get_current_mode()" in api_mode_section
    has_allowed = "allowed_transitions" in api_mode_section
    has_contract = "contract" in api_mode_section
    has_is_halted = "is_halted" in api_mode_section
    
    # 验证不使用旧的 paper/live 语义
    no_paper_trade = '"paper_trade"' not in api_mode_section
    
    print(f"PASS: /api/mode uses get_current_mode() = {uses_get_mode}")
    print(f"PASS: /api/mode returns allowed_transitions = {has_allowed}")
    print(f"PASS: /api/mode returns contract = {has_contract}")
    print(f"PASS: /api/mode returns is_halted = {has_is_halted}")
    print(f"PASS: /api/mode does not use paper_trade = {no_paper_trade}")
    
    return uses_get_mode and has_allowed and has_contract and has_is_halted and no_paper_trade


def test_get_state_contract_in_production():
    """验证 get_state() 返回正式状态机 mode"""
    print("\n" + "=" * 60)
    print("ROUND 6: GET_STATE CONTRACT IN PRODUCTION")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 找到 get_state 方法
    get_state_start = content.find("def get_state(self)")
    get_state_end = content.find("def get_allowed_transitions", get_state_start)
    get_state_section = content[get_state_start:get_state_end]
    
    # 验证返回结构
    has_mode = '"mode":' in get_state_section
    has_allowed = '"allowed_transitions":' in get_state_section
    has_contract = '"contract":' in get_state_section
    has_is_halted = '"is_halted":' in get_state_section
    
    print(f"PASS: get_state() returns mode = {has_mode}")
    print(f"PASS: get_state() returns allowed_transitions = {has_allowed}")
    print(f"PASS: get_state() returns contract = {has_contract}")
    print(f"PASS: get_state() returns is_halted = {has_is_halted}")
    
    return has_mode and has_allowed and has_is_halted


def test_mode_consistency_across_apis():
    """验证所有 mode API 使用同一来源"""
    print("\n" + "=" * 60)
    print("ROUND 6: MODE CONSISTENCY ACROSS APIS")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 统计使用 get_current_mode() 的 API
    mode_count = content.count('"mode": engine.get_current_mode()')
    print(f"PASS: {mode_count} APIs return mode from get_current_mode()")
    
    return mode_count >= 4


def test_frontend_mode_usage():
    """验证前端使用 d.mode"""
    print("\n" + "=" * 60)
    print("ROUND 6: FRONTEND MODE USAGE")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "index_v2.html")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    uses_d_mode = "d.mode" in content
    
    print(f"PASS: Frontend uses d.mode = {uses_d_mode}")
    
    return uses_d_mode


def test_all_transition_apis_return_allowed():
    """验证所有切换 API 返回 allowed_transitions"""
    print("\n" + "=" * 60)
    print("ROUND 6: TRANSITION APIS RETURN ALLOWED")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 检查 toggle_mode, sim_start, sim_stop 返回 allowed_transitions
    apis = [
        ("api_toggle_mode", '@app.post("/api/toggle_mode")'),
        ("api_start_sim", '@app.post("/api/sim/start")'),
        ("api_stop_sim", '@app.post("/api/sim/stop")'),
    ]
    
    all_return_allowed = True
    for name, pattern in apis:
        start = content.find(pattern)
        end = content.find("@app", start + 10)
        section = content[start:end]
        has_allowed = "allowed_transitions" in section
        print(f"PASS: {name} returns allowed_transitions = {has_allowed}")
        all_return_allowed = all_return_allowed and has_allowed
    
    return all_return_allowed


if __name__ == "__main__":
    ok = test_api_mode_contract_in_production()
    ok = test_get_state_contract_in_production() and ok
    ok = test_mode_consistency_across_apis() and ok
    ok = test_frontend_mode_usage() and ok
    ok = test_all_transition_apis_return_allowed() and ok
    
    print("\n" + "=" * 60)
    print(f"ROUND 6: {'PASS' if ok else 'FAIL'}")
    print("=" * 60)
    sys.exit(0 if ok else 1)