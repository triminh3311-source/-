import streamlit as st
import pandas as pd
import pandas_ta as ta
import requests
import time

# --- 页面配置 ---
st.set_page_config(page_title="币安实时派发猎手 V10", layout="wide", page_icon="☠️")
st.title("☠️ 币安实时派发猎手 V10 (伪装直连版)")
st.markdown("""
**数据源：** 直接通过 HTTP 协议伪装浏览器访问 **Binance Futures (fapi)**。
**延迟：** 实时 (Real-time)。
**目标：** 扫描 **15分钟** 级别出现 **派发 (Distribution)** 特征的山寨币。
""")
st.divider()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚡ 扫描控制")
    # 强制 15m，因为你要抓这个级别的
    st.info("周期锁定：15分钟 (15m)")
    st.warning("⚠️ 为了防止被封，每次扫描间隔建议大于 1 分钟。")
    scan_btn = st.button("🚀 启动实时扫描", type="primary")

# --- 核心：伪装成浏览器获取数据 ---
def get_binance_klines(symbol, interval='15m', limit=50):
    base_url = "https://fapi.binance.com/fapi/v1/klines"
    
    # 伪装请求头 (关键！)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    params = {
        'symbol': symbol.replace('/', ''), # 币安格式是 BTCUSDT，不是 BTC/USDT
        'interval': interval,
        'limit': limit
    }
    
    try:
        # 发送请求，设置 2秒 超时，快速失败
        response = requests.get(base_url, headers=headers, params=params, timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            # 币安返回格式: [Open time, Open, High, Low, Close, Volume, ...]
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                'close_time', 'quote_asset_volume', 'number_of_trades', 
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 数据类型转换
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            return df
        else:
            return None
    except Exception:
        return None

# --- 核心名单：最活跃的 80 个山寨币 (人工精选高波动) ---
TARGET_COINS = [
    'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'DOGEUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT',
    'PNUTUSDT', 'ACTUSDT', 'NEIROUSDT', 'GOATUSDT', 'MOODENGUSDT', 'LUCEUSDT', 'HIPPOUSDT', 
    'WIFUSDT', 'PEPEUSDT', 'BONKUSDT', 'FLOKIUSDT', 'BOMEUSDT', 'MEMEUSDT', 'TURBOUSDT',
    'ORDIUSDT', 'SATSUSDT', 'RATSUSDT', 'TIAUSDT', 'SEIUSDT', 'SUIUSDT', 'APTUSDT', 'ARBUSDT',
    'OPUSDT', 'LDOUSDT', 'ENAUSDT', 'ETHFIUSDT', 'PENDLEUSDT', 'WLDUSDT', 'RNDRUSDT', 'FETUSDT',
    'TAOUSDT', 'JUPUSDT', 'PYTHUSDT', 'JTOUSDT', 'RAYUSDT', 'TNSRUSDT', 'ZKUSDT', 'STRKUSDT',
    'BLURUSDT', 'GMTUSDT', 'APEUSDT', 'SANDUSDT', 'MANAUSDT', 'AXSUSDT', 'GALAUSDT', 'IMXUSDT',
    'FILUSDT', 'NEARUSDT', 'ATOMUSDT', 'DOTUSDT', 'LTCUSDT', 'BCHUSDT', 'ETCUSDT', 'UNIUSDT',
    'AAVEUSDT', 'CRVUSDT', 'MKRUSDT', 'SNXUSDT', 'DYDXUSDT', 'COMPUSDT', '1INCHUSDT', 'RUNEUSDT',
    'INJUSDT', 'STXUSDT', 'KASUSDT', 'FTMUSDT', 'TRXUSDT', 'ALGOUSDT', 'VETUSDT', 'XLMUSDT',
    'NOTUSDT', 'DOGSUSDT', 'HMSTRUSDT', 'CATIUSDT', 'CETUSUSDT', 'COWUSDT', 'THEUSDT'
]

def analyze_distribution(df, symbol):
    if df is None or df.empty: return None
    
    # 计算指标
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    score = 0
    signals = []
    
    # --- 派发特征逻辑 ---
    
    # 1. 上影线 (UT/Pinbar)
    # 只要当前K线或者上一根K线，上影线长度超过实体
    curr_body = abs(curr['close'] - curr['open'])
    curr_upper = curr['high'] - max(curr['close'], curr['open'])
    
    if curr_upper > (curr_body * 1.2): # 稍微宽松点，只要有明显针
        score += 30
        signals.append("当前插针")
        
    # 2. RSI 相对高位
    if curr['rsi'] > 65:
        score += 20
        signals.append(f"RSI高({int(curr['rsi'])})")
    elif curr['rsi'] > 60:
        score += 10
        
    # 3. 假突破 (Trap)
    # 当前K线最高价 > 过去10根K线最高价，但收盘没收上去
    past_high = df['high'].iloc[-12:-2].max()
    if curr['high'] > past_high and curr['close'] < past_high:
        score += 40
        signals.append("🔴假突破")
        
    # 4. 阴跌 (连续阴线)
    if curr['close'] < curr['open'] and prev['close'] < prev['open']:
        score += 10
        
    if score >= 20: # 只要有一点特征就返回，宁可误报不可漏报
        return {
            "币种": symbol.replace('USDT', ''),
            "现价": curr['close'],
            "RSI": round(curr['rsi'], 1),
            "信号": " + ".join(signals),
            "分数": score
        }
    return None

# --- 执行逻辑 ---
if scan_btn:
    st.write(f"🚀 正在通过隐身通道扫描 {len(TARGET_COINS)} 个币种...")
    progress = st.progress(0)
    
    results = []
    success_count = 0
    
    # 建立占位符，扫描到一个显示一个
    result_container = st.container()
    
    for i, sym in enumerate(TARGET_COINS):
        # 获取数据
        df = get_binance_klines(sym)
        
        if df is not None:
            success_count += 1
            res = analyze_distribution(df, sym)
            if res:
                results.append(res)
                # 实时显示高分目标
                if res['分数'] >= 40:
                    with result_container:
