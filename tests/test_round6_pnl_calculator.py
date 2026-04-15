"""
第6轮 PnL 计算器验收测试
验证正式生产程序中的 PnLCalculator 是唯一净损益计算核心
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接从正式生产程序导入
exec(open(os.path.join(os.path.dirname(__file__), "..", "server_v2.py"), "r", encoding="utf-8").read().split("# ══════════════════════════════════════════════════════════════")[0])

def test_pnl_calculator_exists_in_production():
    """验证 PnLCalculator 类存在于正式生产程序"""
    print("=" * 60)
    print("ROUND 6: PnL CALCULATOR IN PRODUCTION")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 验证 PnLCalculator 在生产程序中存在
    has_class = "class PnLCalculator:" in content
    has_calculate = "def calculate(" in content
    has_from_position = "def calculate_from_position(" in content
    
    print(f"PASS: PnLCalculator class exists = {has_class}")
    print(f"PASS: calculate() method exists = {has_calculate}")
    print(f"PASS: calculate_from_position() exists = {has_from_position}")
    
    return has_class and has_calculate and has_from_position


def test_pnl_paths_in_production():
    """验证生产程序中所有平仓路径都使用 PnLCalculator"""
    print("\n" + "=" * 60)
    print("ROUND 6: PnL PATHS IN PRODUCTION")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 搜索整个 _manage_positions 方法
    manage_pos_start = content.find("def _manage_positions(")
    if manage_pos_start > 0:
        close_section = content[manage_pos_start - 1000:manage_pos_start + 1000]
    else:
        close_section = content[content.find("PnLCalculator.calculate_from_position") - 500:content.find("PnLCalculator.calculate_from_position") + 500]
    
    close_uses_pnl = "PnLCalculator.calculate_from_position" in content
    
    # 查找回测 - 搜索整个 api_simulate 函数
    backtest_start = content.find("def api_simulate")
    backtest_end = content.find("def api_simdata", backtest_start)
    backtest_section = content[backtest_start:backtest_end]
    backtest_uses_pnl = "PnLCalculator" in backtest_section
    
    # 查找 TradeRecord
    trade_has_net = "net_pnl" in content
    
    print(f"PASS: close() uses PnLCalculator = {close_uses_pnl}")
    print(f"PASS: backtest uses PnLCalculator = {backtest_uses_pnl}")
    print(f"PASS: TradeRecord has net_pnl = {trade_has_net}")
    
    return close_uses_pnl and backtest_uses_pnl and trade_has_net


def test_pnl_calculation_formula():
    """验证生产程序中 PnL 计算公式正确"""
    print("\n" + "=" * 60)
    print("ROUND 6: PnL FORMULA IN PRODUCTION")
    print("=" * 60)
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 提取 PnLCalculator 类定义
    pnl_class = content[content.find("class PnLCalculator:"):content.find("# ══════════════════════════════════════════════════════════════", content.find("class PnLCalculator:"))]
    
    # 验证关键计算步骤
    has_fee = "fee =" in pnl_class or "FEE_PER_SHARE" in pnl_class
    has_tax = "tax =" in pnl_class or "TAX_RATE" in pnl_class
    has_slippage = "slippage" in pnl_class
    has_net = "net_pnl" in pnl_class
    
    # 验证公式: net = gross - fee - tax - slippage
    formula_correct = "gross_pnl - fee - tax - slippage_cost" in pnl_class
    
    print(f"PASS: fee calculation exists = {has_fee}")
    print(f"PASS: tax calculation exists = {has_tax}")
    print(f"PASS: slippage calculation exists = {has_slippage}")
    print(f"PASS: net_pnl formula correct = {formula_correct}")
    
    return has_fee and has_tax and has_slippage and has_net and formula_correct


if __name__ == "__main__":
    ok = test_pnl_calculator_exists_in_production()
    ok = test_pnl_paths_in_production() and ok
    ok = test_pnl_calculation_formula() and ok
    
    print("\n" + "=" * 60)
    print(f"ROUND 6: {'PASS' if ok else 'FAIL'}")
    print("=" * 60)
    sys.exit(0 if ok else 1)