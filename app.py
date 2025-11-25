import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time

# --- 页面设置 ---
st.set_page_config(page_title="全景威科夫仪表盘 V7", layout="wide", page_icon="💀")
st.title("💀 威科夫全景仪表盘 V7 (做空专用)")
st.markdown("""
**逻辑大改：** 不再隐藏数据。这里列出**全市场成交量前 50** 的币种。
**评分系统：** 只要上涨乏力、RSI超买、出现长上影线，**熊市分数 (Bear Score)** 就会越高。
*分数越高，派发（做顶）嫌疑越大。*
""")
st.divider()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 扫描参数")
    timeframe = st.selectbox("分析周期 (推荐 4h 看趋势)", ['15m', '1h', '4h', '1d'], index=2)
    st.info("系统将获取币安合约成交量 Top 50 的实时数据。")
    scan_btn = st.button("🔄 刷新全市场数据", type="primary")

# --- 核心数据获取 ---
@st.cache_data(ttl=60)
def get_top_coins():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    try:
        # 获取所有行情
        tickers = exchange.fetch_tickers()
        # 筛选 USDT 合约
        valid = [t for s, t in tickers.items() if '/USDT' in s]
        # 按成交额排序，取前 50
        sorted_tickers = sorted(valid, key=lambda x: x['quoteVolume'], reverse=True)[:50]
        return exchange, [t['symbol'] for t in sorted_tickers]
    except Exception as e:
        st.error(f"连接交易所失败: {e}")
        return exchange, []

def analyze_coin(exchange, symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=50)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # 计算指标
        # 1. RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        current_rsi = df['rsi'].iloc[-1]
        
        # 2. 上影线比例 (Upper Wick)
        curr = df.iloc[-1]
        body = abs(curr['close'] - curr['open'])
        upper_wick = curr['high'] - max(curr['close'], curr['open'])
        # 避免除以0
        wick_ratio = upper_wick / (body + 0.00001) 
        
        # 3. 价格位置 (Price Location)
        # 当前价格处于过去 50 根K线的什么位置 (0=最低, 1=最高)
        period_high = df['high'].max()
        period_low = df['low'].min()
        location = (curr['close'] - period_low) / (period_high - period_low)
        
        # --- 🐻 熊市分数计算 (Bear Score) ---
        score = 0
        reasons = []
        
        # A. RSI 评分
        if current_rsi > 70: 
            score += 30
            reasons.append("RSI超买")
        elif current_rsi > 60:
            score += 10
            
        # B. 上影线评分 (UT 嫌疑)
        if wick_ratio > 1.5: # 影线比实体长1.5倍
            score += 40
            reasons.append("长上影线(UT)")
        elif wick_ratio > 0.8:
            score += 20
            
        # C. 高位评分
        if location > 0.85: # 处于近期高位
            score += 20
            reasons.append("处于高位")
            
        # D. 假突破判定 (刚才突破前高现在跌回)
        prev_high = df['high'].iloc[:-1].max() # 不含当前的过去高点
        if curr['high'] > prev_high and curr['close'] < prev_high:
            score += 50 # 这是一个极强的做空信号
            reasons.append("🔴假突破(UTAD)")

        return {
            "币种": symbol,
            "现价": curr['close'],
            "RSI": round(current_rsi, 1),
            "位置": f"{location*100:.0f}%",
            "上影线": f"{wick_ratio:.1f}倍",
            "熊市分数": score,
            "特征": ", ".join(reasons) if reasons else "无明显异常"
        }
        
    except:
        return None

# --- 执行逻辑 ---
if scan_btn:
    st.write("📡 正在连接币安接口，拉取 Top 50 数据...")
    progress = st.progress(0)
    
    exchange, symbols = get_top_coins()
    if not symbols:
        st.error("无法获取币种列表，请稍后再试。")
    else:
        results = []
        for i, sym in enumerate(symbols):
            data = analyze_coin(exchange, sym, timeframe)
            if data:
                results.append(data)
            progress.progress((i + 1) / len(symbols))
        
        progress.empty()
        
        # 将结果转换为 DataFrame
        df_res = pd.DataFrame(results)
        
        # 按“熊市分数”从高到低排序
        df_res = df_res.sort_values(by="熊市分数", ascending=False)
        
        # --- 展示区域 1: 极品做空机会 (分数 > 60) ---
        top_picks = df_res[df_res['熊市分数'] >= 50]
        
        st.subheader("🚨 高危预警 (极高派发嫌疑)")
        if not top_picks.empty:
            for index, row in top_picks.iterrows():
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 3])
                    c1.markdown(f"### {row['币种']}")
                    c2.metric("熊市分数", row['熊市分数'])
                    c3.metric("RSI", row['RSI'])
                    c4.metric("位置", row['位置'])
                    c5.error(f"**{row['特征']}**")
                    st.divider()
        else:
            st.info("当前没有 >50 分的完美做空形态，请看下方的全市场排行。")

        # --- 展示区域 2: 全市场大表 (你一定能看到数据) ---
        st.subheader("📋 全市场监控列表 (按熊市分数排序)")
        st.dataframe(
            df_res,
            column_config={
                "熊市分数": st.column_config.ProgressColumn(
                    "做空潜力",
                    help="分数越高，顶部特征越明显",
                    format="%d",
                    min_value=0,
                    max_value=120,
                ),
            },
            hide_index=True,
            use_container_width=True
        )
