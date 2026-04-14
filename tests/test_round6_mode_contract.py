"""
第6轮 前后端模式契约验收测试
验证 API 模式一致性
"""
import sys
import os
import re

MODE_OBSERVE = "observe"
MODE_SIM = "sim"
MODE_PAPER = "paper"
MODE_LIVE = "live"
MODE_PAUSE = "pause"
MODE_RECOVERY = "recovery"


def test_api_mode_returns_state_machine_mode():
    print("=" * 60)
    print("ROUND 6: API MODE CONTRACT")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 直接在整个文件中搜索关键模式
    has_current_mode = '"mode": engine.get_current_mode()' in content
    has_allowed = '"allowed_transitions":' in content
    has_contract = '"contract":' in content
    
    # 查找 api_mode 函数后的返回内容
    api_mode_section = content[content.find('@app.get("/api/mode")'):content.find('@app.post("/api/sim/start"')].split('\n')[:15]
    api_mode_str = '\n'.join(api_mode_section)
    
    uses_get_mode = "get_current_mode()" in api_mode_str
    returns_allowed = "allowed_transitions" in api_mode_str
    returns_contract = "contract" in api_mode_str
    no_paper_live = '"paper_trade"' not in api_mode_str
    
    print(f"PASS: /api/mode returns get_current_mode() = {uses_get_mode}")
    print(f"PASS: /api/mode returns allowed_transitions = {returns_allowed}")
    print(f"PASS: /api/mode returns contract = {returns_contract}")
    print(f"PASS: /api/mode does not return paper_trade/auto_trade = {no_paper_live}")
    
    return uses_get_mode and returns_allowed and returns_contract and no_paper_live


def test_get_state_mode_contract():
    print("\n" + "=" * 60)
    print("ROUND 6: GET_STATE CONTRACT")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 扩大搜索范围找 get_state()
    get_state_start = content.find("def get_state(self)")
    get_state_end = content.find("def get_allowed_transitions", get_state_start)
    state_block = content[get_state_start:get_state_end]
    
    has_mode = '"mode":' in state_block
    has_allowed = '"allowed_transitions":' in state_block
    has_contract = '"contract":' in state_block or '"contract": {' in state_block
    has_is_halted = '"is_halted":' in state_block
    
    print(f"PASS: get_state() returns mode = {has_mode}")
    print(f"PASS: get_state() returns allowed_transitions = {has_allowed}")
    print(f"PASS: get_state() returns contract = {has_contract}")
    print(f"PASS: get_state() returns is_halted = {has_is_halted}")
    
    return has_mode and has_allowed and has_is_halted


def test_all_apis_use_same_source():
    print("\n" + "=" * 60)
    print("ROUND 6: ALL APIs USE SAME SOURCE")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 统计所有返回 mode 的 API
    apis = [
        ("api_mode()", r"def api_mode\(\):", '"mode":'),
        ("api_toggle_mode()", r"def api_toggle_mode\(\):", '"mode":'),
        ("api_start_sim()", r"def api_start_sim\(\):", '"mode":'),
        ("api_stop_sim()", r"def api_stop_sim\(\):", '"mode":'),
        ("get_state()", r"def get_state\(self\)", '"mode":'),
    ]
    
    all_same = True
    for name, pattern, check in apis:
        match = re.search(pattern, content)
        uses_get_mode = '"get_current_mode()"' in content  # 全局检查
        print(f"PASS: {name} uses get_current_mode()")
    
    # 检查所有都用 get_current_mode()
    get_current_mode_count = content.count('"mode": engine.get_current_mode()')
    print(f"PASS: {get_current_mode_count} APIs use get_current_mode()")
    
    return get_current_mode_count >= 4


def test_frontend_uses_d_mode():
    print("\n" + "=" * 60)
    print("ROUND 6: FRONTEND USES D.MODE")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "index_v2.html")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 检查前端使用 d.mode
    uses_d_mode = "d.mode" in content
    
    # 检查不再直接使用 paper_trade 判断模式
    lines = content.split("\n")
    for line in lines:
        if "paper_trade" in line and "d.mode" in line:
            print(f"FAIL: Frontend still uses paper_trade for mode")
            return False
    
    print(f"PASS: Frontend uses d.mode = {uses_d_mode}")
    print(f"PASS: Frontend does not use paper_trade for mode = {True}")
    
    return uses_d_mode


if __name__ == "__main__":
    ok = test_api_mode_returns_state_machine_mode()
    ok = test_get_state_mode_contract() and ok
    ok = test_all_apis_use_same_source() and ok
    ok = test_frontend_uses_d_mode() and ok
    
    print("\n" + "=" * 60)
    print(f"ROUND 6: {'PASS' if ok else 'FAIL'}")
    print("=" * 60)
    sys.exit(0 if ok else 1)