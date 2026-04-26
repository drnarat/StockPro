import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
from settrade_v2 import Investor

# --- 1. SET PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="SRAN AI Full-Stock Intelligence")

# --- 2. SIDEBAR: FULL TUNING PANEL ---
with st.sidebar:
    st.header("🔑 API Connectivity")
    input_app_id = st.text_input("App ID")
    input_app_secret = st.text_input("App Secret", type="password")
    gemini_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.header("⚙️ Advanced Indicator Tuning")
    
    with st.expander("📈 Trend (MA/EMA)", expanded=True):
        sma_fast = st.slider("SMA Fast", 5, 50, 20)
        sma_slow = st.slider("SMA Slow", 50, 200, 100)
        ema_len = st.slider("EMA Period", 5, 100, 9)
        
    with st.expander("🚀 Momentum (RSI/MACD/Stoch)"):
        rsi_len = st.slider("RSI Period", 2, 30, 14)
        macd_fast = st.number_input("MACD Fast", 8, 20, 12)
        macd_slow = st.number_input("MACD Slow", 21, 40, 26)
        macd_sig = st.number_input("MACD Signal", 5, 15, 9)
        stoch_k = st.slider("Stochastic %K", 5, 30, 14)
        stoch_d = st.slider("Stochastic %D", 1, 10, 3)

    with st.expander("🌪 Volatility & Volume"):
        bb_len = st.slider("Bollinger Period", 5, 50, 20)
        atr_len = st.slider("ATR Period", 5, 30, 14)

# --- 3. CREATE TABS ---
tab1, tab2 = st.tabs(["🔍 Full Market Scanner", "🧠 30-Day Deep Insight AI"])

# --- 4. CORE FUNCTIONS ---
def init_market():
    try:
        investor = Investor(app_id=input_app_id, app_secret=input_app_secret, app_code="SANDBOX", broker_id="SANDBOX")
        return investor.MarketData()
    except: return None

def calculate_full_metrics(df):
    """คำนวณ Indicators ทุกตัวที่เลือกไว้"""
    # Trend
    df['SMA_F'] = ta.sma(df['last'], length=sma_fast)
    df['SMA_S'] = ta.sma(df['last'], length=sma_slow)
    df['EMA_9'] = ta.ema(df['last'], length=ema_len)
    
    # Momentum
    df['RSI'] = ta.rsi(df['last'], length=rsi_len)
    macd = ta.macd(df['last'], fast=macd_fast, slow=macd_slow, signal=macd_sig)
    df = pd.concat([df, macd], axis=1)
    stoch = ta.stoch(df['high'], df['low'], df['last'], k=stoch_k, d=stoch_d)
    df = pd.concat([df, stoch], axis=1)
    
    # Volatility
    bbands = ta.bbands(df['last'], length=bb_len)
    df = pd.concat([df, bbands], axis=1)
    df['ATR'] = ta.atr(df['high'], df['low'], df['last'], length=atr_len)
    
    # Volume
    df['OBV'] = ta.obv(df['last'], df['volume'])
    return df

# --- 5. TAB 1: FULL SCANNER ---
with tab1:
    st.header("Comprehensive Technical Scan")
    stock_list = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
    
    if st.button("🚀 Run Full Market Scan"):
        market = init_market()
        if market:
            with st.spinner("กำลังประมวลผลอินดิเคเตอร์ทุกตัว..."):
                scan_data = []
                for symbol in stock_list:
                    try:
                        res = market.get_candlestick(symbol, "1D", 250)
                        df = calculate_full_metrics(pd.DataFrame(res))
                        last = df.iloc[-1]
                        
                        # สร้างสรุปข้อมูล
                        scan_data.append({
                            "Symbol": symbol,
                            "Price": last['last'],
                            "RSI": round(last['RSI'], 2),
                            "MACD": round(last[f'MACD_{macd_fast}_{macd_slow}_{macd_sig}'], 2),
                            "SMA_F/S": f"{round(last['SMA_F'],1)}/{round(last['SMA_S'],1)}",
                            "EMA_9": round(last['EMA_9'], 2),
                            "Stoch_%K": round(last[f'STOCK_{stoch_k}_{stoch_d}_3'], 2),
                            "ATR": round(last['ATR'], 2),
                            "OBV": f"{last['OBV']:,.0f}",
                            "BB_Upper": round(last[f'BBU_{bb_len}_2.0'], 2)
                        })
                    except: continue
                st.dataframe(pd.DataFrame(scan_data), use_container_width=True)
        else: st.error("กรุณาเชื่อมต่อ API")

# --- 6. TAB 2: AI INSIGHT (1 MONTH) ---
with tab2:
    st.header("🧠 30-Day Deep Insight AI (Gemini)")
    stock_target = st.text_input("ระบุชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze Recent 1-Month"):
        if not gemini_key: st.warning("ใส่ Gemini Key ใน Sidebar")
        else:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            with st.spinner("AI กำลังวิเคราะห์ข้อมูล 30 วันที่ผ่านมา..."):
                prompt = f"วิเคราะห์หุ้น {stock_target} ใน SET: 1.ธุรกิจ 2.ข่าวเด่นใน 1 เดือนนี้ 3.Sentiment ล่าสุด 4.ปัจจัยเสี่ยงสัปดาห์หน้า"
                response = model.generate_content(prompt)
                st.markdown(response.text)
