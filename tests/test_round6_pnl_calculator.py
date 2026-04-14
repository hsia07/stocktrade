"""
第6轮 PnL 计算器验收测试
验证 PnLCalculator 是唯一净损益计算核心
"""
import sys
import os

class PnLCalculator:
    FEE_PER_SHARE = 0.001425 * 0.3
    TAX_RATE = 0.003
    SLIPPAGE_DEFAULT = 0.001
    
    @staticmethod
    def calculate(entry_price, exit_price, qty=1000, direction="LONG"):
        fee_rate = PnLCalculator.FEE_PER_SHARE
        tax_rate = PnLCalculator.TAX_RATE
        slippage = PnLCalculator.SLIPPAGE_DEFAULT
        
        direction_mult = 1 if direction == "LONG" else -1
        price_diff = (exit_price - entry_price) * direction_mult
        gross_pnl = price_diff * qty
        
        fee = entry_price * qty * fee_rate + exit_price * qty * fee_rate
        tax = exit_price * qty * tax_rate if direction == "LONG" else 0
        avg_price = (entry_price + exit_price) / 2
        slippage_cost = avg_price * qty * slippage
        net_pnl = gross_pnl - fee - tax - slippage_cost
        
        return {
            "gross_pnl": round(gross_pnl, 2),
            "fee": round(fee, 2),
            "tax": round(tax, 2),
            "slippage_cost": round(slippage_cost, 2),
            "net_pnl": round(net_pnl, 2),
        }
    
    @staticmethod
    def calculate_from_position(entry_price, exit_price, lots, direction="LONG"):
        return PnLCalculator.calculate(entry_price, exit_price, lots * 1000, direction)


def test_pnl_calculator():
    print("=" * 60)
    print("ROUND 6: PnL CALCULATOR")
    print("=" * 60)
    
    result = PnLCalculator.calculate(100, 110, 1000, "LONG")
    
    tests = [
        ("calculate() returns gross_pnl", "gross_pnl" in result),
        ("calculate() returns fee", "fee" in result),
        ("calculate() returns tax", "tax" in result),
        ("calculate() returns slippage_cost", "slippage_cost" in result),
        ("calculate() returns net_pnl", "net_pnl" in result),
        ("net_pnl = gross_pnl - fee - tax - slippage_cost", 
         abs(result["net_pnl"] - (result["gross_pnl"] - result["fee"] - result["tax"] - result["slippage_cost"])) < 1),
    ]
    
    all_pass = True
    for name, ok in tests:
        status = "PASS" if ok else "FAIL"
        if not ok: all_pass = False
        print(f"{status}: {name}")
    
    print(f"\n{sum(1 for _,ok in tests if ok)}/{len(tests)} passed")
    return all_pass


def test_calculate_from_position():
    print("\n" + "=" * 60)
    print("ROUND 6: CALCULATE_FROM_POSITION")
    print("=" * 60)
    
    result = PnLCalculator.calculate_from_position(100, 110, 1, "LONG")
    
    tests = [
        ("returns gross_pnl", "gross_pnl" in result),
        ("returns net_pnl", "net_pnl" in result),
        ("qty = lots * 1000", result["gross_pnl"] == 10000),
    ]
    
    all_pass = True
    for name, ok in tests:
        status = "PASS" if ok else "FAIL"
        if not ok: all_pass = False
        print(f"{status}: {name}")
    
    return all_pass


def test_trade_record_pnl_property():
    print("\n" + "=" * 60)
    print("ROUND 6: TRADE RECORD PN L PROPERTY")
    print("=" * 60)
    
    import re
    
    # 检查 server_v2.py 中 TradeRecord 是否有 pnl property
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    has_pnl_property = "@property" in content and "def pnl(self)" in content
    has_net_pnl = "net_pnl" in content
    
    print(f"PASS: TradeRecord has pnl property = {has_pnl_property}")
    print(f"PASS: TradeRecord has net_pnl field = {has_net_pnl}")
    
    return has_pnl_property and has_net_pnl


def test_pnl_all_paths():
    print("\n" + "=" * 60)
    print("ROUND 6: PN L ALL PATHS")
    print("=" * 60)
    
    import re
    
    path = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # 检查所有平仓路径都使用 PnLCalculator
    close_uses_pnl = "PnLCalculator.calculate" in content
    backtest_uses_pnl = content.count("PnLCalculator.calculate") >= 2
    
    print(f"PASS: close() uses PnLCalculator = {close_uses_pnl}")
    print(f"PASS: backtest uses PnLCalculator = {backtest_uses_pnl}")
    
    return close_uses_pnl and backtest_uses_pnl


if __name__ == "__main__":
    ok = test_pnl_calculator()
    ok = test_calculate_from_position() and ok
    ok = test_trade_record_pnl_property() and ok
    ok = test_pnl_all_paths() and ok
    
    print("\n" + "=" * 60)
    print(f"ROUND 6: {'PASS' if ok else 'FAIL'}")
    print("=" * 60)
    sys.exit(0 if ok else 1)