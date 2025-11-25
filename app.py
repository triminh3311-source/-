import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time

# --- 页面配置 ---
st.set_page_config(page_title="15分钟山寨币派发猎手", layout="wide", page_icon="🩸")
st.title("🩸 15分钟山寨币派发猎手 (Top 100)")
st.markdown("""
**策略目标：** 扫描前 100 热门山寨币，寻找 **15分钟级别** 的派发结构。
**派发定义：** 1. **UT (假突破):** 突破前高后迅速跌回。
2. **SOW (弱势信号):** 高位长上影线/阴包阳。
3. **RSI 过热:** 短线严重超买。
""")
st.divider()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 扫描控制")
    # 既然你要找15分钟的，默认就锁死在 15m
    timeframe = st.selectbox("时间周期", ['15m', '1h'], index=0)
    st.warning("⚠️ 扫描 100 个币需要约 2 分钟，请耐心等待进度条走完。")
    scan_btn = st.button("🚀 开始扫描", type="primary")

# --- 硬核 100 币种名单 (直接写死，防止API获取失败) ---
# 包含当前(2025)热门的 Meme, AI, 公链等
TARGET_COINS = [
    'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'LINK/USDT', 
    'PNUT/USDT', 'ACT/USDT', 'NEIRO/USDT', 'GOAT/USDT', 'MOODENG/USDT', 'LUCE/USDT', 'HIPPO/USDT', # 新热门
    'WIF/USDT', 'PEPE/USDT', 'BONK/USDT', 'FLOKI/USDT', 'BOME/USDT', 'MEME/USDT', 'TURBO/USDT',
    'ORDI/USDT', 'SATS/USDT', 'RATS/USDT', 'TIA/USDT', 'SEI/USDT', 'SUI/USDT', 'APT/USDT', 'ARB/USDT',
    'OP/USDT', 'LDO/USDT', 'ENA/USDT', 'ETHFI/USDT', 'PENDLE/USDT', 'WLD/USDT', 'RNDR/USDT', 'FET/USDT',
    'TAO/USDT', 'JUP/USDT', 'PYTH/USDT', 'JTO/USDT', 'RAY/USDT', 'TNSR/USDT', 'ZK/USDT', 'STRK/USDT',
    'BLUR/USDT', 'GMT/USDT', 'APE/USDT', 'SAND/USDT', 'MANA/USDT', 'AXS/USDT', 'GALA/USDT', 'IMX/USDT',
    'FIL/USDT', 'NEAR/USDT', 'ATOM/USDT', 'DOT/USDT', 'LTC/USDT', 'BCH/USDT', 'ETC/USDT', 'UNI/USDT',
    'AAVE/USDT', 'CRV/USDT', 'MKR/USDT', 'SNX/USDT', 'DYDX/USDT', 'COMP/USDT', '1INCH/USDT', 'RUNE/USDT',
    'INJ/USDT', 'STX/USDT', 'KAS/USDT', 'FTM/USDT', 'TRX/USDT', 'ALGO/USDT', 'VET/USDT', 'XLM/USDT',
    'EGLD/USDT', 'EOS/USDT', 'XTZ/USDT', 'THETA/USDT', 'FLOW/USDT', 'CHZ/USDT', 'ENJ/USDT', 'ZEC/USDT',
    'IOTA/USDT', 'NEO/USDT', 'KLAY/USDT', 'MINA/USDT', 'QNT/USDT', 'HBAR/USDT', 'CKB/USDT', 'LUNC/USDT',
    'IO/USDT', 'NOT/USDT', 'DOGS/USDT', 'HMSTR/USDT', 'CATI/USDT', 'KAIA/USDT', 'CETUS/USDT', 'COW/USDT'
]

def check_15m_distribution(exchange, symbol):
    try:
        # 获取 50 根 15分钟 K线
        bars = exchange.fetch_ohlcv(symbol, '15m', limit=50)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # 计算 RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        curr = df.iloc[-1]   # 当前K线 (进行中)
        prev = df.iloc[-2]   # 上一根K线 (已收盘)
        
        # --- 派发信号逻辑 ---
        signals = []
        score = 0
        
        # 1. UT (上冲回落) 逻辑
        # 只要当前K线 or 上一根K线，留下了很长的上影线
        # 定义上影线长度
        upper_wick_curr = curr['high'] - max(curr['close'], curr['open'])
        body_curr = abs(curr['close'] - curr['open'])
        
        upper_wick_prev = prev['high'] - max(prev['close'], prev['open'])
        body_prev = abs(prev['close'] - prev['open'])
        
        # 如果上影线 > 实体的 1.5 倍，视为抛压
        if upper_wick_curr > (body_curr * 1.5 + 0.0001):
            signals.append("当前K线插针")
            score += 30
        elif upper_wick_prev > (body_prev * 1.5 + 0.0001):
            signals.append("前K线插针")
            score += 20
            
        # 2. 假突破 (Trap)
        # 过去 20 根的高点
        past_high = df['high'].iloc[-20:-2].max()
        if (curr['high'] > past_high and curr['close'] < past_high) or \
           (prev['high'] > past_high and prev['close'] < past_high):
            signals.append("🔴假突破(UT)")
            score += 50
            
        # 3. RSI 过热
        if curr['rsi'] > 70:
            signals.append(f"RSI超买({int(curr['rsi'])})")
            score += 20
        elif curr['rsi'] > 65:
            score += 10
            
        # 4. 阴包阳 (吞没形态)
        # 如果上一根是阳线，当前是阴线，且吃掉了上一根的实体
        if prev['close'] > prev['open'] and curr['close'] < curr['open']:
            if curr['open'] >= prev['close'] and curr['close'] <= prev['open']:
                signals.append("看跌吞没")
                score += 30

        if score > 0:
            return {
                "币种": symbol,
                "现价": curr['close'],
                "分数": score,
                "信号": " + ".join(signals),
                "RSI": round(curr['rsi'], 1)
            }
            
    except Exception:
        return None # 出错直接跳过，不报错
    return None

# --- 执行 ---
if scan_btn:
    st.write(f"🔍 正在扫描 {len(TARGET_COINS)} 个山寨币的 15m 结构...")
    progress_bar = st.progress(0)
    
    # 实例化交易所 (必须加 enableRateLimit)
    exchange = ccxt.binance({
        'options': {'defaultType': 'future'}, 
        'enableRateLimit': True,
        'timeout': 10000 
    })
    
    results = []
    
    for i, sym in enumerate(TARGET_COINS):
        res = check_15m_distribution(exchange, sym)
        if res:
            results.append(res)
        
        # 更新进度
        progress_bar.progress((i + 1) / len(TARGET_COINS))
        # 稍微延迟一下，防止被封 IP
        time.sleep(0.05)
        
    progress_bar.empty()
    
    if results:
        # 转换为 DataFrame 并排序
        df = pd.DataFrame(results)
        df = df.sort_values(by="分数", ascending=False)
        
        # 只展示分数 > 20 的（过滤掉杂波）
        strong_signals = df[df['分数'] >= 20]
        
        if not strong_signals.empty:
            st.success(f"扫描完成！发现 {len(strong_signals)} 个具有派发特征的币种：")
            
            # 使用原生表格展示，清晰明了
            st.dataframe(
                strong_signals[['币种', '现价', 'RSI', '信号', '分数']],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "分数": st.column_config.ProgressColumn(
                        "做空热度", min_value=0, max_value=100, format="%d"
                    )
                }
            )
        else:
            st.warning("所有币种扫描完成，但没有发现强烈的派发形态。当前可能处于横盘或上涨中继。")
            st.write("以下是微弱信号参考：")
            st.dataframe(df, hide_index=True)
            
    else:
        st.error("扫描完成，但没有获取到有效信号。这极其罕见，可能是网络完全中断。")
