import streamlit as st
import ccxt
import pandas as pd
import time

# --- 页面配置 ---
st.set_page_config(page_title="威科夫雷达 V2.0", layout="wide", page_icon="⚡")
st.title("⚡ 威科夫雷达 V2.0 (高灵敏版)")
st.markdown("当前模式：**高灵敏度**。只要出现微小的 Spring 或 UT 结构都会捕捉。")
st.divider()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 参数设置")
    # 默认改成 15m，更容易出信号
    timeframe = st.selectbox("时间周期", ['5m', '15m', '1h', '4h'], index=1) 
    lookback = st.slider("回看K线数量", 5, 60, 20)
    st.info("提示：如果信号太多，请手动切换回 1h 或 4h 过滤噪音。")
    scan_btn = st.button("🚀 开始全市场扫描", type="primary")

@st.cache_data(ttl=30)
def get_market_data():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    # 增加了更多热门山寨币，更容易扫到信号
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 
        'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'LINK/USDT', 'MATIC/USDT',
        'DOT/USDT', 'LTC/USDT', 'OP/USDT', 'ARB/USDT', 'SUI/USDT',
        'APT/USDT', 'RNDR/USDT', 'PEPE/USDT', 'WLD/USDT', 'ORDI/USDT',
        'TIA/USDT', 'NEAR/USDT', 'FIL/USDT', 'INJ/USDT', 'IMX/USDT',
        'SEI/USDT', 'BLUR/USDT', 'GMT/USDT', 'APE/USDT', 'SAND/USDT'
    ]
    return exchange, symbols

def check_signal(exchange, symbol, timeframe, lookback):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=lookback+5)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        curr = df.iloc[-1]
        ref_df = df.iloc[:-2] # 参考过去 N 根
        
        support = ref_df['low'].min()
        resistance = ref_df['high'].max()
        
        # 宽松版逻辑：只要收回即可，对影线长度要求降低到 10%
        body_size = abs(curr['close'] - curr['open'])
        
        # Spring
        if curr['low'] < support and curr['close'] > support:
            lower_wick = min(curr['close'], curr['open']) - curr['low']
            # 只要下影线是实体的 0.1 倍就报警 (之前是0.3)
            if lower_wick > body_size * 0.1: 
                return {
                    "币种": symbol, 
                    "现价": curr['close'], 
                    "信号": "🟢 潜在 Spring (做多)", 
                    "分析": f"价格跌破 {support} 后收回，下影线确认"
                }
                
        # UT
        elif curr['high'] > resistance and curr['close'] < resistance:
            upper_wick = curr['high'] - max(curr['close'], curr['open'])
            if upper_wick > body_size * 0.1:
                return {
                    "币种": symbol, 
                    "现价": curr['close'], 
                    "信号": "🔴 潜在 UT (做空)", 
                    "分析": f"价格突破 {resistance} 后跌回，上影线确认"
                }
    except:
        return None
    return None

if scan_btn:
    progress = st.progress(0)
    status_text = st.empty()
    
    exchange, symbols = get_market_data()
    found = []
    
    for i, s in enumerate(symbols):
        status_text.text(f"正在扫描: {s} ...")
        res = check_signal(exchange, s, timeframe, lookback)
        if res: found.append(res)
        progress.progress((i+1)/len(symbols))
        time.sleep(0.05)
        
    progress.empty()
    status_text.empty()
    
    if found:
        st.success(f"扫描完成！发现 {len(found)} 个潜在机会")
        for row in found:
            with st.container():
                c1, c2, c3 = st.columns([1, 2, 3])
                c1.markdown(f"### {row['币种']}")
                c2.metric("当前价格", row['现价'])
                if "做多" in row['信号']:
                    c3.markdown(f":green_heart: **{row['信号']}**")
                else:
                    c3.markdown(f":boom: **{row['信号']}**")
                c3.caption(row['分析'])
                st.divider()
    else:
        st.warning("当前 15m/1h 周期内暂无信号。建议稍后再试，或盯着几个主流币等待。")

else:
    st.info("👈 请点击左侧按钮开始扫描")
