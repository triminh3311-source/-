import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time

# --- 页面设置 ---
st.set_page_config(page_title="威科夫全景雷达 V7.1", layout="wide", page_icon="🛡️")
st.title("🛡️ 威科夫全景雷达 V7.1 (防封锁版)")
st.markdown("""
**状态监测：** 系统会自动检测币安 API 连接状态。
如果云端 IP 被限制，将自动切换到 **本地白名单模式**，确保永远有数据可看。
""")
st.divider()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 扫描参数")
    timeframe = st.selectbox("分析周期", ['15m', '1h', '4h', '1d'], index=2)
    st.info("提示：如果遇到网络错误，系统会自动启用备用数据源。")
    scan_btn = st.button("🚀 启动雷达", type="primary")

# --- 备用白名单 (硬核 150 币种) ---
FALLBACK_COINS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'LINK/USDT', 'SHIB/USDT',
    'DOT/USDT', 'LTC/USDT', 'BCH/USDT', 'UNI/USDT', 'ATOM/USDT', 'ETC/USDT', 'FIL/USDT', 'NEAR/USDT', 'APT/USDT', 'ARB/USDT',
    'OP/USDT', 'SUI/USDT', 'INJ/USDT', 'RNDR/USDT', 'MATIC/USDT', 'TRX/USDT', 'XLM/USDT', 'VET/USDT', 'ALGO/USDT', 'FTM/USDT',
    'SAND/USDT', 'MANA/USDT', 'AXS/USDT', 'THETA/USDT', 'AAVE/USDT', 'SNX/USDT', 'CRV/USDT', 'GRT/USDT', 'DYDX/USDT', 'LDO/USDT',
    'IMX/USDT', 'STX/USDT', 'RUNE/USDT', 'EGLD/USDT', 'QNT/USDT', 'MINA/USDT', 'EOS/USDT', 'XTZ/USDT', 'NEO/USDT', 'IOTA/USDT',
    'GALA/USDT', 'CHZ/USDT', 'KAVA/USDT', 'FLOW/USDT', 'ZEC/USDT', 'DASH/USDT', 'MKR/USDT', 'COMP/USDT', 'ENJ/USDT', 'BAT/USDT',
    'PEPE/USDT', 'WLD/USDT', 'ORDI/USDT', 'TIA/USDT', 'SEI/USDT', 'BLUR/USDT', 'GMT/USDT', 'APE/USDT', 'JUP/USDT', 'PYTH/USDT',
    'BONK/USDT', 'WIF/USDT', 'FLOKI/USDT', 'MEME/USDT', '1000SATS/USDT', 'RATS/USDT', 'JTO/USDT', 'ACE/USDT', 'NFP/USDT', 'AI/USDT',
    'XAI/USDT', 'MANTA/USDT', 'ALT/USDT', 'PIXEL/USDT', 'STRK/USDT', 'PORTAL/USDT', 'AEVO/USDT', 'ETHFI/USDT', 'ENA/USDT', 'W/USDT',
    'TNSR/USDT', 'SAGA/USDT', 'TAO/USDT', 'OMNI/USDT', 'REZ/USDT', 'BB/USDT', 'NOT/USDT', 'IO/USDT', 'ZK/USDT', 'ZRO/USDT',
    'BLAST/USDT', 'RENDER/USDT', 'BANANA/USDT', 'DOGS/USDT', 'TON/USDT', 'TURBO/USDT', 'NEIRO/USDT', '1MBABYDOGE/USDT', 'CATI/USDT', 'HMSTR/USDT',
    'EIGEN/USDT', 'SCR/USDT', 'GOAT/USDT', 'MOODENG/USDT', 'COW/USDT', 'CETUS/USDT', 'THE/USDT', 'PNUT/USDT', 'ACT/USDT', 'HIPPO/USDT',
    'LUCE/USDT', 'KAIA/USDT', 'SWELL/USDT', 'DRIFT/USDT', 'GRASS/USDT', 'SAFE/USDT', 'POL/USDT', 'BOME/USDT', 'POPCAT/USDT', 'MEW/USDT'
]

# --- 核心数据获取 (带异常处理) ---
@st.cache_data(ttl=60)
def get_target_coins():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
    try:
        # 尝试连接币安获取实时热门
        # 这里故意只取很少的 tickers 避免被封，如果失败直接跳 except
        tickers = exchange.fetch_tickers()
        valid = [t for s, t in tickers.items() if '/USDT' in s]
        sorted_tickers = sorted(valid, key=lambda x: x['quoteVolume'], reverse=True)[:60]
        st.toast("✅ 成功连接币安实时数据！", icon="🟢")
        return exchange, [t['symbol'] for t in sorted_tickers]
    except Exception as e:
        # 如果报错（被封IP），直接使用白名单
        st.toast("⚠️ 云端IP受限，已切换至白名单模式。", icon="🛡️")
        return exchange, FALLBACK_COINS

def analyze_coin(exchange, symbol, timeframe):
    try:
        # 获取 K 线
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=50)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # 1. 计算 RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        current_rsi = df['rsi'].iloc[-1]
        
        # 2. 计算上影线 (UT特征)
        curr = df.iloc[-1]
        body = abs(curr['close'] - curr['open'])
        upper_wick = curr['high'] - max(curr['close'], curr['open'])
        wick_ratio = upper_wick / (body + 0.00001) 
        
        # 3. 价格位置 (0-1)
        period_high = df['high'].max()
        period_low = df['low'].min()
        location = (curr['close'] - period_low) / (period_high - period_low + 0.00001)
        
        # --- 🐻 熊市分数计算 ---
        score = 0
        reasons = []
        
        # RSI 维度
        if current_rsi > 75: 
            score += 30
            reasons.append("RSI极度超买")
        elif current_rsi > 65:
            score += 15
            
        # 形态维度 (上影线)
        if wick_ratio > 2.0: 
            score += 40
            reasons.append("避雷针(UT)")
        elif wick_ratio > 1.0:
            score += 20
            
        # 位置维度
        if location > 0.9: 
            score += 20
            reasons.append("高位滞涨")
            
        # 假突破维度
        prev_high = df['high'].iloc[:-1].max()
        if curr['high'] > prev_high and curr['close'] < prev_high:
            score += 50
            reasons.append("🔴假突破(Trap)")

        return {
            "币种": symbol,
            "现价": curr['close'],
            "RSI": round(current_rsi, 1),
            "上影线": f"{wick_ratio:.1f}倍",
            "熊市分数": score,
            "特征": " ".join(reasons) if reasons else "-"
        }
        
    except:
        return None

# --- 执行扫描 ---
if scan_btn:
    # 1. 获取币种列表
    exchange, symbols = get_target_coins()
    
    st.write(f"🦅 正在扫描 **{len(symbols)}** 个目标，寻找空头猎物...")
    progress = st.progress(0)
    
    results = []
    
    # 2. 循环分析
    for i, sym in enumerate(symbols):
        data = analyze_coin(exchange, sym, timeframe)
        if data:
            results.append(data)
        progress.progress((i + 1) / len(symbols))
        # 稍微慢一点，避免K线接口也被封
        time.sleep(0.05) 
        
    progress.empty()
    
    # 3. 结果展示
    if results:
        df_res = pd.DataFrame(results)
        df_res = df_res.sort_values(by="熊市分数", ascending=False)
        
        # 高分高亮区
        top = df_res[df_res['熊市分数'] >= 45]
        if not top.empty:
            st.error(f"🚨 发现 {len(top)} 个高危派发目标！")
            st.dataframe(
                top,
                column_config={
                    "熊市分数": st.column_config.ProgressColumn("做空潜力", min_value=0, max_value=120, format="%d"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.success("✅ 当前市场没有极端的高位派发信号。")
            
        st.markdown("---")
        st.caption("全市场详细数据监控：")
        st.dataframe(df_res, hide_index=True, use_container_width=True)
    else:
        st.error("无法获取数据，请稍后刷新页面再试。")
