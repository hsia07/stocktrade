# Modular Trading Interface Layout Blueprint

## R026: 模组交易界面优化 / 实作 / 蓝图 / 策略市场

### Purpose
Define the blueprint architecture for modular trading interface components.

### Layout Structure

#### 1. Dashboard Widget (dashboard.py)
- **Component Type**: Dashboard
- **Position**: Top-left (x:0, y:0)
- **Size**: 800x600
- **Config**: layout="default", widgets=3
- **Linkage**: Links to blueprint layout definition

#### 2. Strategy Panel (strategy_panel.py)
- **Component Type**: StrategyPanel
- **Position**: Top-right (x:800, y:0)
- **Size**: 400x600
- **Config**: filter="all", selected=None
- **Linkage**: Displays strategy market data

#### 3. Market Overview (market_overview.py)
- **Component Type**: MarketOverview
- **Position**: Bottom (x:0, y:600)
- **Size**: 1200x400
- **Config**: sort_by="volume", ascending=false
- **Linkage**: Shows market data for strategy market

### Blueprint-to-Implementation Linkage
- Blueprint defines layout → UI components implement layout
- Each component is modular and independently replaceable
- Strategy market integration: strategy_panel.py displays, market_overview.py shows market data
- NO runtime trading logic in blueprint
- NO core execution / risk / strategy code

### Strategy Market Integration
- **Display**: Strategy names, performance metrics, market filter
- **Interaction**: Select strategy, filter by market type
- **Data Flow**: UI components → display only, NO order execution
- **Scope**: UI display + interaction only, NO trading decisions

### Modular Design
- Components can be replaced independently
- Dashboard widget → swapable
- Strategy panel → swapable
- Market overview → swapable
- Blueprint ensures consistent layout across swaps
