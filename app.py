import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time

# --- 页面配置 ---
st.set_page_config(page_title="威科夫空头猎手 V6", layout="wide", page_icon="🩸")
st.title("🩸 威科夫空头猎手 V6 (抓捕派发/UT)")
st.markdown("""
**核心策略：** 寻找 **Distribution (派发)** 结构。
**主要信号：** 1. **UT (Upthrust):** 假突破前高，收盘跌回。
2. **SOW (Sign of Weakness):** 涨不动了，高位出现长上影线。
3. **RSI 背离:** 价格新高，RSI 没新高 (主力在悄悄出货)。
""")
st.divider()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 空头参数")
    # 找顶部通常用 4h 或 1d 比较稳，但 15m/1h 适合抓日内高点
    timeframe = st.selectbox("时间周期", ['15m', '1h', '4h', '1d'], index=1)
    
    # 回看周期：判断是否在高位的参照物
    lookback = st.slider("结构回看 K 线数", 20, 100, 50)
    
    st.warning("⚠️ 熊市不言底，牛市不言顶。请配合成交量确认。")
    scan_btn = st.button("💀 启动空头扫描", type="primary")

# --- 硬核名单：全市场波动最大的 100+ 个币 ---
TOP_COINS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ORDI/USDT', 'SATS/USDT', 'RATS/USDT', 
    'TIA/USDT', 'SEI/USDT', 'WLD/USDT', 'FIL/USDT', 'LINK/USDT', 'AVAX/USDT', 'DOGE/USDT',
    'PEPE/USDT', 'WIF/USDT', 'BONK/USDT', 'FLOKI/USDT', 'MEME/USDT', 'BOME/USDT', 'JUP/USDT',
    'PYTH/USDT', 'JTO/USDT', 'RAY/USDT', 'NEAR/USDT', 'RNDR/USDT', 'FET/USDT', 'AGIX/USDT',
    'OCEAN/USDT', 'W/USDT', 'ENA/USDT', 'ETHFI/USDT', 'PENDLE/USDT', 'SSV/USDT', 'LDO/USDT',
    'OP/USDT', 'ARB/USDT', 'STRK/USDT', 'MATIC/USDT', 'DYDX/USDT', 'GALA/USDT', 'SAND/USDT',
    'MANA/USDT', 'APE/USDT', 'BLUR/USDT', 'GMT/USDT', 'AXS/USDT', 'CHZ/USDT', 'TRX/USDT',
    'LTC/USDT', 'BCH/USDT', 'ETC/USDT', 'EOS/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT',
    'ATOM/USDT', 'SUI/USDT', 'APT/USDT', 'INJ/USDT', 'KAS/USDT', 'STX/USDT', 'FTM/USDT',
    'IMX/USDT', 'RUNE/USDT', 'SNX/USDT', 'CRV/USDT', 'AAVE/USDT', 'COMP/USDT', 'MKR/USDT',
    '1000SATS/USDT', 'ALT/USDT', 'PIXEL/USDT', 'AI/USDT', 'XAI/USDT', 'ACE/USDT', 'NFP/USDT',
    'PORTAL/USDT', 'AEVO/USDT', 'TNSR/USDT', 'SAGA/USDT', 'TAO/USDT', 'ZK/USDT', 'NOT/USDT',
    'IO/USDT', 'ZRO/USDT', 'LISTA/USDT', 'BLAST/USDT', 'DOGS/USDT', 'CATI/USDT', 'HMSTR/USDT',
    'NEIRO/USDT', 'TURBO/USDT', '1MBABYDOGE/USDT', 'ACT/USDT', 'PNUT/USDT', 'MOODENG/USDT',
    'GOAT/USDT', 'HIPPO/USDT', 'THE/USDT', 'LUCE/USDT', 'CETUS/USDT', 'COW/USDT', 'KAIA/USDT'
]

def check_distribution(exchange, symbol, timeframe, lookback):
    try:
        # 获取足够多的 K 线以计算 RSI
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=lookback + 20)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # 计算 RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # 获取当前K线 和 之前的参照系
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 定义过去的“高点区域” (Resistance)
        # 取过去 N 根K线的最高价（不包含当前这根）
        past_high = df['high'].iloc[-lookback:-1].max()
        
        # --- 信号逻辑 1: UT (上冲回落 / 假突破) ---
        # 今天的最高价冲破了过去的高点，但收盘价没站稳，收了回来
        is_ut = False
        if curr['high'] > past_high and curr['close'] < past_high:
            is_ut = True
            
        # --- 信号逻辑 2: 射击之星 (Shooting Star) ---
        # 上影线很长，实体很小，且位于相对高位
        body = abs(curr['close'] - curr['open'])
        upper_wick = curr['high'] - max(curr['close'], curr['open'])
        is_shooting_star = False
        # 上影线是实体的 2 倍以上
        if upper_wick > body * 2:
            is_shooting_star = True
            
        # --- 信号逻辑 3: RSI 严重超买 ---
        is_overbought = curr['rsi'] > 70
        
        # --- 组合判断 (只要满足其一即可入选) ---
        
        # 场景 A: 经典 UT (突破失败 + 收跌)
        if is_ut and curr['close'] < curr['open']:
            return {
                "Symbol": symbol,
                "Price": curr['close'],
                "RSI": round(curr['rsi'], 2),
                "Signal": "🔴 UT (假突破)",
                "Desc": f"突破前高 {past_high} 失败，主力诱多"
            }
            
        # 场景 B: 高位长上影线 (SOW) + 相对高位
        # 只有当价格接近过去高点时（95%水位），出射击之星才有效
        if is_shooting_star and curr['high'] >= past_high * 0.95:
             return {
                "Symbol": symbol,
                "Price": curr['close'],
                "RSI": round(curr['rsi'], 2),
                "Signal": "⚠️ 射击之星 (抛压)",
                "Desc": "高位出现长上影线，空头抵抗强烈"
            }
            
        # 场景 C: 极度超买 (RSI > 75)
        if curr['rsi'] > 75:
             return {
                "Symbol": symbol,
                "Price": curr['close'],
                "RSI": round(curr['rsi'], 2),
                "Signal": "🔥 极度超买",
                "Desc": f"RSI 高达 {curr['rsi']:.1f}，随时可能回调"
            }

    except Exception as e:
        return None
    return None

# --- 执行扫描 ---
if scan_btn:
    st.write(f"🦅 正在高空巡航，扫描 **{len(TOP_COINS)}** 个目标的顶部结构...")
    progress = st.progress(0)
    
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    found = []
    
    result_col = st.container()
    
    for i, sym in enumerate(TOP_COINS):
        res = check_distribution(exchange, sym, timeframe, lookback)
        
        if res:
            found.append(res)
            with result_col:
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"### {res['Symbol']}")
                c2.metric("现价", res['Price'])
                c3.metric("RSI", res['RSI'])
                c4.error(f"**{res['Signal']}**")
                st.caption(res['Desc'])
                st.divider()
                
        progress.progress((i + 1) / len(TOP_COINS))
        time.sleep(0.05)
        
    progress.empty()
    
    if len(found) == 0:
        st.info("当前市场没有发现明显的顶部派发结构。可能是因为大盘正在单边下跌（Markdown阶段），没有反弹给你空。")
    else:
        st.success(f"扫描结束！发现 {len(found)} 个潜在做空目标。")
