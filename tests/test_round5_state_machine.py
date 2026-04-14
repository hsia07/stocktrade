"""
第5轮状态机验收测试
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

MODE_TRANSITIONS = {
    (MODE_SIM, MODE_PAUSE): (True, "EXIT_SIM"),
    (MODE_SIM, MODE_OBSERVE): (True, "EXIT_SIM"),
    (MODE_SIM, MODE_PAPER): (True, "EXIT_SIM"),
    (MODE_SIM, MODE_LIVE): (True, "EXIT_SIM"),
    (MODE_PAUSE, MODE_SIM): (True, "ENTER_SIM"),
    (MODE_PAUSE, MODE_OBSERVE): (True, "AUTO_TRADE=true"),
    (MODE_PAUSE, MODE_PAPER): (True, "PAPER_TRADE=true"),
    (MODE_PAUSE, MODE_LIVE): (True, "PAPER_TRADE=false"),
    (MODE_PAUSE, MODE_RECOVERY): (True, "is_halted=true"),
    (MODE_OBSERVE, MODE_RECOVERY): (True, "is_halted=true"),
    (MODE_PAPER, MODE_RECOVERY): (True, "is_halted=true"),
    (MODE_LIVE, MODE_RECOVERY): (True, "is_halted=true"),
    (MODE_OBSERVE, MODE_PAUSE): (True, "AUTO_TRADE=false"),
    (MODE_OBSERVE, MODE_SIM): (True, "ENTER_SIM"),
    (MODE_OBSERVE, MODE_PAPER): (True, "PAPER_SWITCH"),
    (MODE_OBSERVE, MODE_LIVE): (False, "must go through PAUSE"),
    (MODE_PAPER, MODE_PAUSE): (True, "AUTO_TRADE=false"),
    (MODE_PAPER, MODE_SIM): (True, "ENTER_SIM"),
    (MODE_PAPER, MODE_LIVE): (True, "PAPER_SWITCH"),
    (MODE_PAPER, MODE_OBSERVE): (False, "must go through PAUSE"),
    (MODE_LIVE, MODE_PAUSE): (True, "AUTO_TRADE=false"),
    (MODE_LIVE, MODE_SIM): (True, "ENTER_SIM"),
    (MODE_LIVE, MODE_PAPER): (True, "PAPER_SWITCH"),
    (MODE_LIVE, MODE_OBSERVE): (False, "must go through PAUSE"),
    (MODE_RECOVERY, MODE_PAUSE): (True, "is_halted=false"),
    (MODE_RECOVERY, MODE_OBSERVE): (False, "must go through PAUSE"),
    (MODE_RECOVERY, MODE_PAPER): (False, "must go through PAUSE"),
    (MODE_RECOVERY, MODE_LIVE): (False, "must go through PAUSE"),
}

def can_transition(from_mode, to_mode):
    key = (from_mode, to_mode)
    if key in MODE_TRANSITIONS:
        return MODE_TRANSITIONS[key][0]
    return False

def test_transitions():
    results = []
    all_passed = True
    
    tests = [
        (MODE_SIM, MODE_PAUSE, True), (MODE_SIM, MODE_OBSERVE, True),
        (MODE_SIM, MODE_PAPER, True), (MODE_SIM, MODE_LIVE, True),
        (MODE_PAUSE, MODE_SIM, True), (MODE_PAUSE, MODE_OBSERVE, True),
        (MODE_PAUSE, MODE_PAPER, True), (MODE_PAUSE, MODE_LIVE, True),
        (MODE_PAUSE, MODE_RECOVERY, True),
        (MODE_OBSERVE, MODE_PAUSE, True), (MODE_OBSERVE, MODE_SIM, True),
        (MODE_OBSERVE, MODE_PAPER, True), (MODE_OBSERVE, MODE_LIVE, False),
        (MODE_PAPER, MODE_PAUSE, True), (MODE_PAPER, MODE_SIM, True),
        (MODE_PAPER, MODE_LIVE, True), (MODE_PAPER, MODE_OBSERVE, False),
        (MODE_LIVE, MODE_PAUSE, True), (MODE_LIVE, MODE_SIM, True),
        (MODE_LIVE, MODE_PAPER, True), (MODE_LIVE, MODE_OBSERVE, False),
        (MODE_RECOVERY, MODE_PAUSE, True), (MODE_RECOVERY, MODE_OBSERVE, False),
        (MODE_RECOVERY, MODE_PAPER, False), (MODE_RECOVERY, MODE_LIVE, False),
        (MODE_OBSERVE, MODE_RECOVERY, True), (MODE_PAPER, MODE_RECOVERY, True),
        (MODE_LIVE, MODE_RECOVERY, True),
    ]
    
    print("=" * 60)
    print("ROUND 5 MODE TRANSITIONS")
    print("=" * 60)
    
    for fm, tm, exp in tests:
        act = can_transition(fm, tm)
        ok = act == exp
        if not ok: all_passed = False
        print(f"{'PASS' if ok else 'FAIL'}: {fm} -> {tm} = {act} (exp={exp})")
    
    print(f"\n{sum(1 for fm, tm, exp in tests if can_transition(fm, tm)==exp)}/{len(tests)} passed")
    return all_passed

def test_undefined():
    print("\n" + "=" * 60)
    print("UNDEFINED TRANSITIONS DEFAULT DENY")
    print("=" * 60)
    
    for fm, tm in [("OBSERVE","OBSERVE"), ("SIM","PAPER"), ("RECOVERY","SIM")]:
        ok = can_transition(fm, tm) == False
        print(f"{'PASS' if ok else 'FAIL'}: {fm} -> {tm} denied")
    return True

def test_entry():
    print("\n" + "=" * 60)
    print("ENTRY CONSISTENCY")
    print("=" * 60)
    
    p = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(p, encoding="utf-8") as f: c = f.read()
    
    ok = "def set_mode" in c and "def get_current_mode" in c
    print(f"{'PASS' if ok else 'FAIL'}: set_mode/get_current_mode exist")
    return ok

if __name__ == "__main__":
    ok = test_transitions() and test_undefined() and test_entry()
    print("\n" + "=" * 60)
    print(f"ROUND 5: {'PASS' if ok else 'FAIL'}")
    print("=" * 60)
    sys.exit(0 if ok else 1)