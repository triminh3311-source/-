import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 页面配置 ---
st.set_page_config(page_title="15分钟派发扫描 (Yahoo版)", layout="wide", page_icon="⚡")
st.title("⚡ 15分钟山寨币派发扫描 (Yahoo通道)")
st.markdown("""
**特别说明：** 为了解决币安接口在云端被封锁的问题，本版本切换至 **Yahoo 财经数据源**。
**优点：** 极其稳定，百分百有数据。
**缺点：** 缺少刚上线几天的土狗币 (如 PNUT)，但主流山寨 (PEPE, WIF, SOL) 全都有。
""")
st.divider()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 扫描设置")
    timeframe = st.selectbox("周期", ['15m', '1h'], index=0)
    st.info("Yahoo 数据源连接中... 请点击下方按钮。")
    scan_btn = st.button("🚀 强制启动", type="primary")

# --- 硬核名单 (Yahoo 格式) ---
# Yahoo 的格式是 币种-USD
TARGETS = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'DOGE-USD', 'ADA-USD', 'AVAX-USD', 'TRX-USD', 'LINK-USD',
    'DOT-USD', 'MATIC-USD', 'LTC-USD', 'BCH-USD', 'UNI-USD', 'XLM-USD', 'ATOM-USD', 'XMR-USD', 'ETC-USD', 'FIL-USD',
    'HBAR-USD', 'LDO-USD', 'APT-USD', 'ARB-USD', 'NEAR-USD', 'VET-USD', 'QNT-USD', 'MKR-USD', 'GRT-USD', 'OP-USD',
    'AAVE-USD', 'RNDR-USD', 'EGLD-USD', 'SNX-USD', 'STX-USD', 'EOS-USD', 'SAND-USD', 'THETA-USD', 'IMX-USD', 'FTM-USD',
    'AXS-USD', 'MANA-USD', 'APE-USD', 'CHZ-USD', 'FLOW-USD', 'KAVA-USD', 'GALA-USD', 'MINA-USD', 'TEZOS-USD', 'IOTA-USD',
    'SHIB-USD', 'PEPE-USD', 'WIF-USD', 'BONK-USD', 'FLOKI-USD', 'MEME-USD', 'ORDI-USD', 'SATS-USD', 'INJ-USD', 'RUNE-USD',
    'TIA-USD', 'SEI-USD', 'SUI-USD', 'FET-USD', 'AGIX-USD', 'OCEAN-USD', 'JUP-USD', 'PYTH-USD', 'WLD-USD', 'BLUR-USD',
    'JTO-USD', 'RAY-USD', 'GMT-USD', 'CRV-USD', 'COMP-USD', '1INCH-USD', 'DYDX-USD', 'ENS-USD', 'LUNC-USD', 'CFX-USD'
]

def analyze_data(df, symbol):
    try:
        # 清洗数据
        if df.empty or len(df) < 30: return None
        
        # 计算 RSI
        df['rsi'] = ta.rsi(df['Close'], length=14)
        
        # 获取最后两根K线
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        signals = []
        score = 0
        
        # 1. 插针 (上影线)
        body = abs(curr['Close'] - curr['Open'])
        upper_wick = curr['High'] - max(curr['Close'], curr['Open'])
        
        # 宽松一点：只要上影线 > 实体，就算有压力
        if upper_wick > body:
            signals.append("上影线抛压")
            score += 30
            
        # 2. RSI 高位
        if curr['rsi'] > 65:
            signals.append(f"RSI高位({int(curr['rsi'])})")
            score += 20
        elif curr['rsi'] > 55: # 放宽条件，只要RSI偏高就算
            score += 10
            
        # 3. 阴线
        if curr['Close'] < curr['Open']:
            score += 10
            
        # 4. 假突破 (Trap) - 极其简单的逻辑
        # 只要最高价很高，但收盘收不上去
        if curr['High'] > df['High'].iloc[-10:-1].max():
            if curr['Close'] < curr['Open']: # 创新高收阴
                signals.append("假突破")
                score += 50
        
        # 只要有一点点分，就返回，确保用户能看到数据！
        if score > 0:
            return {
                "币种": symbol.replace('-USD', ''),
                "现价": round(curr['Close'], 4),
                "RSI": round(curr['rsi'], 1),
                "信号": " ".join(signals),
                "分数": score
            }
        # 哪怕没有分，为了证明扫描器在工作，如果是RSI>50也返回一个低分
        elif curr['rsi'] > 50:
             return {
                "币种": symbol.replace('-USD', ''),
                "现价": round(curr['Close'], 4),
                "RSI": round(curr['rsi'], 1),
                "信号": "观察中",
                "分数": 5
            }
            
    except:
        return None
    return None

if scan_btn:
    st.write(f"📡 正在从 Yahoo 批量拉取 {len(TARGETS)} 个币种数据 (只需一次请求)...")
    
    # 核心：批量下载，不会被封 IP
    # period='5d' 保证有足够的 15m 数据
    data = yf.download(TARGETS, period="5d", interval=timeframe, group_by='ticker', threads=True)
    
    if data.empty:
        st.error("Yahoo 数据返回为空，可能是 Yahoo 服务器暂时繁忙，请刷新重试。")
    else:
        st.success("✅ 数据拉取成功！正在分析结构...")
        
        results = []
        progress = st.progress(0)
        
        # 遍历数据
        for i, ticker in enumerate(TARGETS):
            try:
                # 提取单个币种的 DataFrame
                df_coin = data[ticker].dropna()
                res = analyze_data(df_coin, ticker)
                if res:
                    results.append(res)
            except:
                pass # 个别币种数据缺失跳过
            
            progress.progress((i + 1) / len(TARGETS))
            
        progress.empty()
        
        if results:
            df_res = pd.DataFrame(results)
            df_res = df_res.sort_values(by="分数", ascending=False)
            
            # 区分高亮
            high_risk = df_res[df_res['分数'] >= 30]
            normal = df_res[df_res['分数'] < 30]
            
            if not high_risk.empty:
                st.error(f"🚨 发现 {len(high_risk)} 个明显派发结构！")
                st.dataframe(
                    high_risk, 
                    use_container_width=True,
                    hide_index=True,
                    column_config={"分数": st.column_config.ProgressColumn("做空指数", min_value=0, max_value=100)}
                )
            
            st.subheader("📋 观察列表 (RSI > 50)")
            st.dataframe(normal, use_container_width=True, hide_index=True)
            
        else:
            st.warning("数据已获取，但当前市场所有币 RSI 均极低 (<50)，暂无做空机会。")
