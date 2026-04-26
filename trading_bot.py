import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings
import logging

# Configuration & Security
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)

# --- 1. UI SETUP ---
st.set_page_config(layout="wide", page_title="SRAN AI Stock Intelligence", page_icon="📈")

# --- 2. SIDEBAR: CREDENTIALS & TUNING ---
with st.sidebar:
    st.header("🔑 API Connectivity")
    app_id = st.text_input("Settrade App ID", placeholder="กรอก App ID")
    app_secret = st.text_input("Settrade App Secret", type="password")
    gemini_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.header("⚙️ Strategy Parameters")
    with st.expander("📈 Indicators Tuning", expanded=True):
        sma_f = st.slider("SMA Fast", 5, 50, 20)
        sma_s = st.slider("SMA Slow", 50, 200, 100)
        rsi_p = st.slider("RSI Period", 5, 30, 14)
        adx_p = st.slider("ADX Period", 7, 21, 14)

# --- 3. CORE ENGINE CLASS ---
class StockEngine:
    def __init__(self, a_id, a_secret):
        try:
            self.investor = Investor(app_id=a_id, app_secret=a_secret, app_code="SANDBOX", broker_id="SANDBOX")
            self.market = self.investor.MarketData()
        except Exception as e:
            st.sidebar.error(f"Settrade Connection Failed: {e}")
            self.market = None

    def fetch_and_analyze(self, symbol):
        """ดึงข้อมูลและคำนวณอินดิเคเตอร์แบบปลอดภัย"""
        try:
            res = self.market.get_candlestick(symbol, "1D", 250)
            df = pd.DataFrame(res)
            if df.empty or len(df) < sma_s: return None
            
            # Trend & Momentum
            df['SMA_F'] = ta.sma(df['last'], length=sma_f)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s)
            df['RSI'] = ta.rsi(df['last'], length=rsi_p)
            
            # ADX Strength
            adx_df = ta.adx(df['high'], df['low'], df['last'], length=adx_p)
            df = pd.concat([df, adx_df], axis=1)
            
            # OBV Volume
            df['OBV'] = ta.obv(df['last'], df['volume'])
            
            return df.dropna(subset=['SMA_F', 'SMA_S', 'RSI'])
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Global Scanner", "🧠 AI Deep Insight", "📊 Sentiment Gauge"])

# --- TAB 1: SCANNER ---
with tab1:
    st.header("Technical Market Scanner")
    if st.button("🚀 Start Global Scan"):
        if not (app_id and app_secret):
            st.warning("⚠️ กรุณากรอก Settrade Credentials ใน Sidebar")
        else:
            engine = StockEngine(app_id, app_secret)
            if engine.market:
                with st.spinner("ประมวลผลข้อมูลตลาด..."):
                    stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                    scan_results = []
                    
                    for s in stocks:
                        df = engine.fetch_and_analyze(s)
                        if df is not None and not df.empty:
                            last = df.iloc[-1]
                            adx_col = f"ADX_{adx_p}"
                            
                            scan_results.append({
                                "Symbol": s,
                                "Price": last['last'],
                                "RSI": round(last['RSI'], 2),
                                "Trend": "📈 Bullish" if last['SMA_F'] > last['SMA_S'] else "📉 Bearish",
                                "Strength (ADX)": round(last[adx_col], 1),
                                "Volume (OBV)": f"{last['OBV']:,.0f}"
                            })
                    
                    if scan_results:
                        st.dataframe(pd.DataFrame(scan_results), use_container_width=True)
                    else:
                        st.error("ไม่สามารถดึงข้อมูลได้ โปรดตรวจสอบการเชื่อมต่อ API")

# --- TAB 2: AI INSIGHT ---
with tab2:
    st.header("Gemini 30-Day Analysis")
    stock_input = st.text_input("ชื่อหุ้นที่ต้องการวิเคราะห์", "PTT")
    
    if st.button("🧠 Analyze Recent Activity"):
        if not gemini_key:
            st.warning("⚠️ กรุณาใส่ Gemini API Key ใน Sidebar")
        else:
            try:
                genai.configure(api_key=gemini_key)
                # ค้นหา Model ที่รองรับเพื่อแก้ปัญหา NotFound
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                target_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                
                model = genai.GenerativeModel(target_model)
                with st.spinner(f"AI ({target_model}) กำลังประมวลผลข้อมูล 30 วัน..."):
                    prompt = f"วิเคราะห์หุ้น {stock_input} ในตลาด SET: 1.ธุรกิจ 2.ข่าวเด่นรอบ 30 วัน 3.Sentiment ล่าสุด 4.ปัจจัยเสี่ยงอาทิตย์หน้า ตอบภาษาไทย"
                    response = model.generate_content(prompt)
                    st.success(f"บทวิเคราะห์จาก {target_model}")
                    st.markdown(response.text)
            except Exception as e:
                st.error(f"Gemini API Error: {e}")

# --- TAB 3: SENTIMENT ---
with tab3:
    st.header("Market Sentiment Gauge")
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = 65, # ตัวอย่างค่า Sentiment
        title = {'text': "Market Sentiment (Fear & Greed)"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "#1f77b4"},
            'steps' : [
                {'range': [0, 35], 'color': "#ff4b4b"},
                {'range': [35, 65], 'color': "#f0f2f6"},
                {'range': [65, 100], 'color': "#09ab3b"}]
        }
    ))
    st.plotly_chart(fig, use_container_width=True)
