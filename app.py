import streamlit as st
import ccxt
import pandas as pd
import time

st.set_page_config(page_title="威科夫主力雷达", layout="wide", page_icon="🦉")
st.title("🦉 威科夫主力雷达 (Wyckoff Scanner)")
st.markdown("核心逻辑：捕捉主力资金的 **Spring (弹簧效应)** 和 **UT (上冲回落)** 行为。")
st.divider()

with st.sidebar:
    st.header("⚙️ 参数设置")
    timeframe = st.selectbox("时间周期", ['15m', '1h', '4h', '1d'], index=2)
    lookback = st.slider("回看K线数量", 10, 60, 20)
    scan_btn = st.button("🚀 开始全市场扫描", type="primary")

@st.cache_data(ttl=60)
def get_market_data():
    return ccxt.binance({'options': {'defaultType': 'future'}}), [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 
        'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'LINK/USDT', 'MATIC/USDT',
        'DOT/USDT', 'LTC/USDT', 'OP/USDT', 'ARB/USDT', 'SUI/USDT',
        'APT/USDT', 'RNDR/USDT', 'PEPE/USDT', 'WLD/USDT', 'ORDI/USDT'
    ]

def check_signal(exchange, symbol, timeframe, lookback):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=lookback+5)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        curr = df.iloc[-1]
        ref_df = df.iloc[:-2]
        support = ref_df['low'].min()
        resistance = ref_df['high'].max()
        
        if curr['low'] < support and curr['close'] > support:
            wick = min(curr['close'], curr['open']) - curr['low']
            if wick > abs(curr['close'] - curr['open']) * 0.3:
                return {"币种": symbol, "现价": curr['close'], "信号": "🟢 SPRING (做多)", "分析": f"跌破 {support} 后收回"}
        elif curr['high'] > resistance and curr['close'] < resistance:
            wick = curr['high'] - max(curr['close'], curr['open'])
            if wick > abs(curr['close'] - curr['open']) * 0.3:
                return {"币种": symbol, "现价": curr['close'], "信号": "🔴 UT (做空)", "分析": f"突破 {resistance} 后回落"}
    except: return None

if scan_btn:
    st.write("正在扫描中，请稍候...")
    progress = st.progress(0)
    exchange, symbols = get_market_data()
    found = []
    for i, s in enumerate(symbols):
        res = check_signal(exchange, s, timeframe, lookback)
        if res: found.append(res)
        progress.progress((i+1)/len(symbols))
        time.sleep(0.1)
    progress.empty()
    if found:
        st.success(f"发现 {len(found)} 个机会！")
        for row in found:
            st.markdown(f"### {row['币种']} - {row['信号']}")
            st.write(f"价格: {row['现价']} | 分析: {row['分析']}")
            st.divider()
    else: st.info("暂无明显信号")
