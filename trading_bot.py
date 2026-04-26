import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
from settrade_v2 import Investor
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

# --- 1. SET PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="SRAN AI Intelligence", page_icon="📈")

# --- 2. SIDEBAR CONFIG ---
with st.sidebar:
    st.header("🔑 API Credentials")
    app_id = st.text_input("App ID", placeholder="Settrade App ID")
    app_secret = st.text_input("App Secret", type="password")
    gemini_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.header("⚙️ Strategy Tuning")
    
    with st.expander("📊 Technical Indicators", expanded=True):
        sma_f = st.slider("SMA Fast", 5, 50, 20)
        sma_s = st.slider("SMA Slow", 50, 200, 100)
        rsi_p = st.slider("RSI Period", 5, 30, 14)
        adx_p = st.slider("ADX Period", 7, 21, 14)
        
    with st.expander("🌪 Volatility & Volume"):
        bb_len = st.slider("Bollinger Bands", 10, 50, 20)
        atr_len = st.slider("ATR (Volatility)", 5, 30, 14)

# --- 3. CORE ENGINE ---
class TradingEngine:
    def __init__(self, a_id, a_secret):
        try:
            self.investor = Investor(app_id=a_id, app_secret=a_secret, app_code="SANDBOX", broker_id="SANDBOX")
            self.market = self.investor.MarketData()
        except: self.market = None

    def analyze_stock(self, symbol):
        res = self.market.get_candlestick(symbol, "1D", 250)
        df = pd.DataFrame(res)
        
        # Trend & Momentum
        df['SMA_F'] = ta.sma(df['last'], length=sma_f)
        df['SMA_S'] = ta.sma(df['last'], length=sma_s)
        df['RSI'] = ta.rsi(df['last'], length=rsi_p)
        
        # Trend Strength (ADX)
        adx = ta.adx(df['high'], df['low'], df['last'], length=adx_p)
        
        # Volatility & Volume
        bbands = ta.bbands(df['last'], length=bb_len)
        df['ATR'] = ta.atr(df['high'], df['low'], df['last'], length=atr_len)
        df['OBV'] = ta.obv(df['last'], df['volume'])
        
        return pd.concat([df, adx, bbands], axis=1)

# --- 4. UI TABS ---
tab1, tab2, tab3 = st.tabs(["🔍 Market Scanner", "🧠 AI Deep Analysis", "📊 Sentiment Dashboard"])

# --- TAB 1: SCANNER ---
with tab1:
    st.header("Market Technical Scanner")
    if st.button("🚀 Start Global Scan"):
        engine = TradingEngine(app_id, app_secret)
        if engine.market:
            with st.spinner("Scanning Market Data..."):
                stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                data = []
                for s in stocks:
                    try:
                        df = engine.analyze_stock(s)
                        last = df.iloc[-1]
                        
                        # Trend Logic
                        adx_val = last[f'ADX_{adx_p}']
                        trend_strength = "Strong" if adx_val > 25 else "Weak"
                        
                        data.append({
                            "Symbol": s, "Price": last['last'], "RSI": round(last['RSI'], 2),
                            "Trend": "Bullish" if last['SMA_F'] > last['SMA_S'] else "Bearish",
                            "ADX (Strength)": f"{round(adx_val, 1)} ({trend_strength})",
                            "ATR": round(last['ATR'], 2),
                            "OBV": f"{last['OBV']:,.0f}"
                        })
                    except: continue
                st.dataframe(pd.DataFrame(data), use_container_width=True)
        else: st.info("กรุณากรอก API Credentials ที่ Sidebar")

# --- TAB 2: AI ANALYSIS ---
with tab2:
    st.header("Gemini AI Strategy Advisor")
    target = st.text_input("ชื่อหุ้นสำหรับการวิเคราะห์", "PTT")
    if st.button("🧠 Generate AI Insights"):
        if gemini_key:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            with st.spinner(f"Gemini กำลังอ่านข่าว {target} รอบ 30 วัน..."):
                prompt = f"วิเคราะห์หุ้น {target} ในตลาด SET รอบ 30 วัน: 1.สรุปธุรกิจ 2.ข่าวเด่น 3.Sentiment 4.โอกาสทางเทคนิค"
                resp = model.generate_content(prompt)
                st.markdown(resp.text)
        else: st.warning("ใส่ Gemini Key ใน Sidebar")

# --- TAB 3: SENTIMENT DASHBOARD ---
with tab3:
    st.header("Market Sentiment Visualizer")
    st.info("จำลองการวิเคราะห์ Sentiment จากปริมาณข่าวและการเคลื่อนไหวของราคา (AI Assisted)")
    
    # ตัวอย่างกราฟ Sentiment 
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = 75,
        title = {'text': "Market Greed Index (SET)"},
        gauge = {'axis': {'range': [0, 100]},
                 'bar': {'color': "darkblue"},
                 'steps' : [
                     {'range': [0, 30], 'color': "red"},
                     {'range': [30, 70], 'color': "gray"},
                     {'range': [70, 100], 'color': "green"}]}))
    st.plotly_chart(fig)
