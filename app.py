import streamlit as st
import ccxt
import pandas as pd
import time

# --- 页面配置 ---
st.set_page_config(page_title="山寨币暴利猎手 V3", layout="wide", page_icon="🚀")
st.title("🚀 山寨币暴利猎手 V3 (寻找 TNSR 式震仓)")
st.markdown("""
**核心策略：** 寻找 **Deep Shakeout + V-Shape Reversal** (深跌后暴力V反)。
扫描全网成交量前 100 的热门山寨币，专抓主力骗线。
""")
st.divider()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 猎杀参数")
    timeframe = st.selectbox("时间周期 (建议15m/1h)", ['15m', '1h', '4h'], index=0)
    vol_limit = st.slider("扫描币种数量 (按成交量排名)", 50, 200, 100)
    drop_threshold = st.slider("震仓深度要求 (%)", 1.0, 10.0, 2.0, help="最低点比开盘价跌了多少百分比才算暴跌")
    st.warning("注意：全市场扫描速度较慢，请耐心等待 1-2 分钟。")
    scan_btn = st.button("🔥 启动全网扫描", type="primary")

# --- 核心功能 ---
@st.cache_data(ttl=300) # 缓存5分钟
def get_top_volume_coins(limit=100):
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    try:
        tickers = exchange.fetch_tickers()
        # 筛选 USDT 合约
        valid_tickers = [
            t for s, t in tickers.items() 
            if '/USDT:USDT' in s or ('/USDT' in s and 'future' in t.get('info', {}).get('status', '').lower())
        ]
        # 按成交量排序 (quoteVolume)
        sorted_tickers = sorted(valid_tickers, key=lambda x: x['quoteVolume'], reverse=True)
        # 提取 Symbol
        top_symbols = [t['symbol'] for t in sorted_tickers[:limit]]
        return exchange, top_symbols
    except:
        # 如果获取失败，返回一个保底列表
        return exchange, ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'TNSR/USDT', 'PEPE/USDT', 'WIF/USDT']

def check_shakeout_v_shape(exchange, symbol, timeframe, drop_pct_threshold):
    try:
        # 获取最近 30 根 K 线
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=30)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # 只需要看最近 3 根 K 线有没有发生 V 反
        # 逻辑：
        # 1. 最近 3 根中，有一根K线创了过去 20 根的新低 (Liquidity Grab)
        # 2. 那根K线的跌幅很大 (恐慌制造)
        # 3. 当前价格已经收复了失地 (V反确认)
        
        recent_bars = df.iloc[-3:] # 看最近3根
        past_bars = df.iloc[:-3]   # 过去的
        
        support_low = past_bars['low'].min()
        
        for index, row in recent_bars.iterrows():
            # 条件1: 跌破了之前的震荡区间最低点
            if row['low'] < support_low:
                
                # 计算这根针扎得有多深 (跌幅百分比)
                # (开盘 - 最低) / 开盘
                drop_magnitude = (row['open'] - row['low']) / row['open'] * 100
                
                # 条件2: 跌幅必须足够大 (用户设定的阈值，比如 2%)
                if drop_magnitude >= drop_pct_threshold:
                    
                    # 条件3: 现在的价格必须已经拉回来了
                    # 如果是当前K线，看收盘价；如果是前两根，看最新价
                    current_price = df.iloc[-1]['close']
                    
                    # 价格收复了跌幅的 50% 以上，或者直接站回了支撑位
                    if current_price > (row['low'] + (row['open'] - row['low']) * 0.6):
                        return {
                            "Symbol": symbol,
                            "Price": current_price,
                            "Drop": f"-{drop_magnitude:.2f}%",
                            "Type": "🩸 暴力洗盘 V反",
                            "Desc": f"击穿 {support_low} 后快速拉回"
                        }
        return None

    except:
        return None

# --- 执行扫描 ---
if scan_btn:
    progress_text = st.empty()
    bar = st.progress(0)
    
    with st.spinner("正在从币安获取热门山寨币列表..."):
        exchange, symbols = get_top_volume_coins(vol_limit)
    
    st.info(f"已锁定成交量前 {len(symbols)} 名的币种，开始地毯式搜查...")
    
    found_ops = []
    
    # 建立一个占位符区域，扫描到一个显示一个，不用等全部扫完
    result_container = st.container()
    
    for i, sym in enumerate(symbols):
        progress_text.text(f"正在扫描 ({i+1}/{len(symbols)}): {sym}")
        res = check_shakeout_v_shape(exchange, sym, timeframe, drop_threshold)
        
        if res:
            found_ops.append(res)
            # 实时显示结果
            with result_container:
                cols = st.columns([1, 1, 1, 2])
                cols[0].markdown(f"### {res['Symbol']}")
                cols[1].metric("现价", res['Price'])
                cols[2].error(res['Drop']) # 显示跌幅
                cols[3].success(f"**{res['Type']}**\n\n{res['Desc']}")
                st.divider()

        bar.progress((i + 1) / len(symbols))
        time.sleep(0.05) # 极速模式，稍微减少延迟
        
    bar.empty()
    progress_text.empty()
    
    if not found_ops:
        st.warning(f"扫描了 {len(symbols)} 个币种，当前 15分钟 级别暂无符合【TNSR式暴力洗盘】的形态。主力可能在休息。")
        st.caption("建议：过 15 分钟再点一次，或者去 1h 级别看看。")
