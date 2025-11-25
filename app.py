import streamlit as st
import ccxt
import pandas as pd
import time

# --- 页面配置 ---
st.set_page_config(page_title="山寨币 V 反雷达 V5", layout="wide", page_icon="⚡")
st.title("⚡ 山寨币 V 反雷达 V5 (形态学暴力版)")
st.markdown("""
**核心逻辑更新：** 不再强制要求"跌破前低"。
**只要满足：** 短时间内先暴跌，然后迅速拉升 (V-Shape)，就会被捕获。
*专抓主力暴力洗盘插针。*
""")
st.divider()

# --- 侧边栏参数 ---
with st.sidebar:
    st.header("⚙️ 灵敏度调节")
    # TNSR 这种 15m 级别的 V 反最常见
    timeframe = st.selectbox("时间周期", ['15m', '1h', '4h'], index=0)
    
    # 降低门槛：建议 1.5% - 2.0%。如果设太大，只有崩盘时才有信号。
    volatility_threshold = st.slider("震幅阈值 (%)", 1.0, 5.0, 2.0, help="最近3根K线的高低差至少要达到这个百分比")
    
    recovery_ratio = st.slider("反弹力度 (0.5=反弹一半)", 0.3, 0.9, 0.5, help="从最低点拉回了跌幅的多少？0.5代表V反了一半，0.8代表完全收复失地")
    
    scan_btn = st.button("🚀 启动扫描", type="primary")

# --- 硬核名单 (确保包含高波动山寨) ---
TOP_COINS = [
    'TNSR/USDT', 'PEPE/USDT', 'WIF/USDT', 'ORDI/USDT', 'SOL/USDT', 'BTC/USDT', 'ETH/USDT', 'DOGE/USDT',
    'YGG/USDT', 'GALA/USDT', 'ENA/USDT', 'WLD/USDT', 'TIA/USDT', 'OP/USDT', 'ARB/USDT', 'SUI/USDT',
    'APT/USDT', 'RNDR/USDT', 'NEAR/USDT', 'FET/USDT', 'AGIX/USDT', 'OCEAN/USDT', 'INJ/USDT', 'LDO/USDT',
    'FIL/USDT', 'LINK/USDT', 'MATIC/USDT', 'AVAX/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT', 'LTC/USDT',
    'BCH/USDT', 'UNI/USDT', 'ATOM/USDT', 'ETC/USDT', 'SHIB/USDT', 'FTM/USDT', 'SAND/USDT', 'MANA/USDT',
    'AXS/USDT', 'APE/USDT', 'CHZ/USDT', 'EOS/USDT', 'XTZ/USDT', 'AAVE/USDT', 'CRV/USDT', 'DYDX/USDT',
    '1000SATS/USDT', 'RATS/USDT', 'MEME/USDT', 'BONK/USDT', 'FLOKI/USDT', 'PYTH/USDT', 'JTO/USDT', 'JUP/USDT',
    'ALT/USDT', 'PIXEL/USDT', 'STRK/USDT', 'PORTAL/USDT', 'AEVO/USDT', 'ETHFI/USDT', 'SAGA/USDT', 'TAO/USDT',
    'REZ/USDT', 'BB/USDT', 'NOT/USDT', 'IO/USDT', 'ZK/USDT', 'LISTA/USDT', 'ZRO/USDT', 'BLAST/USDT',
    'BANANA/USDT', 'DOGS/USDT', 'TON/USDT', 'NEIRO/USDT', 'TURBO/USDT', '1MBABYDOGE/USDT', 'CATI/USDT',
    'HMSTR/USDT', 'EIGEN/USDT', 'SCR/USDT', 'GOAT/USDT', 'MOODENG/USDT', 'ACT/USDT', 'PNUT/USDT', 'HIPPO/USDT',
    'THE/USDT', 'LUCE/USDT', 'CETUS/USDT', 'KAIA/USDT', 'COW/USDT', 'GRASS/USDT', 'DRIFT/USDT', 'SWELL/USDT'
]

def check_v_shape(exchange, symbol, timeframe, vol_thresh, rec_ratio):
    try:
        # 获取最近 5 根 K 线，哪怕是极短线的反转也能抓到
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=5)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # 我们只关注最近 3 根 K 线（包含当前这根）
        recent_df = df.iloc[-3:]
        
        # 1. 找这期间的最高价和最低价
        period_high = recent_df['high'].max()
        period_low = recent_df['low'].min()
        period_open = recent_df['open'].iloc[0] # 3根前的开盘价
        current_price = recent_df['close'].iloc[-1]
        
        # 2. 计算最大波动幅度 (High - Low) / High
        volatility = (period_high - period_low) / period_high * 100
        
        # 3. 计算“砸盘深度”：从起始开盘价 到 最低点 跌了多少
        drop_pct = (period_open - period_low) / period_open * 100
        
        # 4. 核心逻辑：
        # 条件A: 波动幅度够大 (哪怕是震荡，只要幅度大就有机会)
        # 条件B: 当前价格已经从最低点拉起来了 (V反)
        
        if volatility > vol_thresh:
            
            # 计算反弹幅度： (现价 - 最低) / (开盘 - 最低)
            # 如果分母太小(没跌)，就忽略
            total_drop = period_open - period_low
            if total_drop == 0: return None
            
            bounce_height = current_price - period_low
            bounce_ratio = bounce_height / total_drop
            
            # 只有当：真的跌了(drop > 0.5%) 并且 反弹力度达标
            if drop_pct > 0.5 and bounce_ratio > rec_ratio:
                return {
                    "Symbol": symbol,
                    "Price": current_price,
                    "Drop": f"{drop_pct:.2f}%",
                    "Bounce": f"拉回 {bounce_ratio*100:.0f}%",
                    "Desc": f"3根K线内深跌 {drop_pct:.2f}% 后强力反弹"
                }
    except:
        return None
    return None

if scan_btn:
    st.write(f"🔍 正在全网扫描 {len(TOP_COINS)} 个高波动山寨币...")
    progress = st.progress(0)
    
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    found = []
    
    # 建立一个即时显示区域
    result_col = st.container()
    
    for i, sym in enumerate(TOP_COINS):
        res = check_v_shape(exchange, sym, timeframe, volatility_threshold, recovery_ratio)
        
        if res:
            found.append(res)
            with result_col:
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"**{res['Symbol']}**")
                c2.write(f"现价: {res['Price']}")
                c3.markdown(f"📉 曾跌: :red[{res['Drop']}]")
                c4.markdown(f"📈 现弹: :green[{res['Bounce']}]")
                st.markdown("---")
                
        progress.progress((i + 1) / len(TOP_COINS))
        time.sleep(0.05)
        
    progress.empty()
    
    if len(found) == 0:
        st.warning("🧐 扫描完成，依然没有捕捉到完美的 V 反形态。")
        st.markdown("""
        **可能原因与建议：**
        1. **市场波动太小：** 当前可能处于“垃圾时间”，没有庄家在干活。
        2. **参数太高：** 试着把 **震幅阈值** 调低到 **1.0%** 试试？
        """)
    else:
        st.success(f"🎯 扫描结束！共发现 {len(found)} 个 V 反结构！")
