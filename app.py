import streamlit as st
import ccxt
import pandas as pd
import time

# --- 页面配置 ---
st.set_page_config(page_title="山寨币暴利猎手 V4 (全火力版)", layout="wide", page_icon="🔥")
st.title("🔥 山寨币暴利猎手 V4 (强制扫描前120名)")
st.markdown("""
**策略：** 强制覆盖币安活跃度最高的 120+ 个山寨币，寻找 **暴力洗盘 (Deep Shakeout) + V反**。
*不再依赖API排名，确保每次都扫满全场。*
""")
st.divider()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 猎杀参数")
    # 默认 15m，这是抓日内 V 反的黄金周期
    timeframe = st.selectbox("时间周期", ['15m', '1h', '4h'], index=0)
    
    # 震仓深度：建议 2% - 3%，太小是噪音，太深可能是真崩盘
    drop_threshold = st.slider("最低跌幅要求 (%)", 1.0, 8.0, 2.0)
    
    st.info("点击按钮后，请耐心等待 2-3 分钟，因为要逐个分析 120 个币的 K 线结构。")
    scan_btn = st.button("🚀 启动地毯式轰炸", type="primary")

# --- 硬核名单：币安合约成交量/热度 Top 120 (手动维护，确保覆盖) ---
# 包含：公链、Meme、AI、RWA、Depin、老主流等板块龙头
TOP_COINS = [
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
    'EIGEN/USDT', 'SCR/USDT', 'GOAT/USDT', 'MOODENG/USDT', 'COW/USDT', 'CETUS/USDT', 'THE/USDT', 'PNUT/USDT', 'ACT/USDT', 'HIPPO/USDT'
]

# --- 核心逻辑 ---
def check_shakeout(exchange, symbol, timeframe, drop_limit):
    try:
        # 获取最近 30 根 K 线
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=30)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # 截取最近 3 根用于判断 V 反
        recent = df.iloc[-3:]
        # 过去的数据用于判断支撑
        past = df.iloc[:-3]
        
        support_low = past['low'].min()
        
        # 遍历最近3根，寻找那一根"插针"的K线
        for idx, row in recent.iterrows():
            # 1. 必须跌破之前的最低点 (猎杀流动性)
            if row['low'] < support_low:
                
                # 2. 计算跌幅 (High - Low) 或者 (Open - Low)
                # 这里用 (Open - Low) 更能体现砸盘力度
                drop_pct = (row['open'] - row['low']) / row['open'] * 100
                
                # 3. 跌幅必须达标 (比如瞬间跌了 2% 以上)
                if drop_pct >= drop_limit:
                    
                    # 4. 判断是否拉回 (V反)
                    # 获取当前最新价格 (最后一根K线的 Close)
                    curr_price = df.iloc[-1]['close']
                    
                    # 拉回逻辑：当前价格 > 那根针的低点 + 跌幅的一半
                    # 也就是说收复了至少 50% 的失地，或者直接翻红
                    recovery_price = row['low'] + (row['open'] - row['low']) * 0.5
                    
                    if curr_price > recovery_price:
                        return {
                            "Symbol": symbol,
                            "Price": curr_price,
                            "Drop": f"-{drop_pct:.2f}%",
                            "Status": "✅ V型反转确认",
                            "Detail": f"击穿 {support_low} 后快速拉回"
                        }
        return None
    except:
        return None

# --- 执行区 ---
if scan_btn:
    st.write(f"📊 准备扫描 **{len(TOP_COINS)}** 个热门币种...")
    progress_bar = st.progress(0)
    result_area = st.container()
    
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    found_count = 0
    
    for i, symbol in enumerate(TOP_COINS):
        # 扫描
        res = check_shakeout(exchange, symbol, timeframe, drop_threshold)
        
        if res:
            found_count += 1
            with result_area:
                c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 3])
                c1.markdown(f"### {res['Symbol']}")
                c2.metric("现价", res['Price'])
                c3.markdown(f":red[**{res['Drop']}**]") # 醒目的跌幅
                c4.success(f"{res['Status']}\n\n{res['Detail']}")
                st.divider()
        
        # 更新进度
        progress_bar.progress((i + 1) / len(TOP_COINS))
        time.sleep(0.05) # 稍微快一点
        
    progress_bar.empty()
    
    if found_count == 0:
        st.warning("⚠️ 扫描完成，当前 15分钟 级别没有发现剧烈的 V 反形态。")
        st.markdown("建议：\n1. 尝试将 **最低跌幅要求** 调低一点 (比如 1.5%)。\n2. 切换到 **1h** 周期看看更大级别的机会。")
    else:
        st.balloons()
        st.success(f"🎯 扫描结束！共发现 {found_count} 个潜在暴利目标！")

else:
    st.info("👈 点击左侧按钮，开始全市场地毯式搜索。")
        st.warning(f"扫描了 {len(symbols)} 个币种，当前 15分钟 级别暂无符合【TNSR式暴力洗盘】的形态。主力可能在休息。")
        st.caption("建议：过 15 分钟再点一次，或者去 1h 级别看看。")
