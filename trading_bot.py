import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings
import logging

# Configuration & Suppressing Warnings
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)

# --- 1. INITIAL UI SETUP ---
st.set_page_config(layout="wide", page_title="SRAN AI Stock Platform", page_icon="📈")

# --- 2. SIDEBAR: CREDENTIALS & TUNING ---
with st.sidebar:
    st.header("🔑 Connectivity Settings")
    # ส่วนของ Settrade ตามที่คุณระบุว่าต้องมีครบ
    c_app_id = st.text_input("APP_ID", placeholder="ระบุ APP_ID")
    c_app_secret = st.text_input("APP_SECRET", type="password")
    c_app_code = st.text_input("APP_CODE", value="SANDBOX")
    c_broker_id = st.text_input("BROKER_ID", value="SANDBOX")
    c_account_no = st.text_input("ACCOUNT_NO", value="Narats-E")
    
    st.divider()
    st.header("🤖 AI Analysis Settings")
    c_gemini_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.header("⚙️ Strategy Parameters")
    with st.expander("📈 Indicators Tuning", expanded=True):
        sma_f = st.slider("SMA Fast (Short-term)", 5, 50, 20)
        sma_s = st.slider("SMA Slow (Long-term)", 50, 200, 100)
        rsi_len = st.slider("RSI Period", 5, 30, 14)
        adx_len = st.slider("ADX (Trend Strength)", 7, 21, 14)

# --- 3. CORE LOGIC ENGINE ---
class StockAIApp:
    def __init__(self, config):
        try:
            self.investor = Investor(
                app_id=config['id'], 
                app_secret=config['secret'], 
                app_code=config['code'], 
                broker_id=config['broker']
            )
            self.market = self.investor.MarketData()
            # ยืนยันสิทธิ์ Account
            self.equity = self.investor.Equity(account_no=config['acc'])
        except Exception as e:
            st.sidebar.error(f"⚠️ Connection Error: {e}")
            self.market = None

    def process_technical_data(self, symbol):
        """คำนวณอินดิเคเตอร์ทุกตัวแบบครบถ้วน"""
        try:
            # ดึงข้อมูลย้อนหลัง 250 วัน เพื่อให้ SMA Slow คำนวณได้
            res = self.market.get_candlestick(symbol, "1D", 250)
            df = pd.DataFrame(res)
            if df.empty or len(df) < sma_s: return None
            
            # --- Technical Library (pandas-ta) ---
            # 1. Trend
            df['SMA_F'] = ta.sma(df['last'], length=sma_f)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s)
            
            # 2. Momentum
            df['RSI'] = ta.rsi(df['last'], length=rsi_len)
            macd = ta.macd(df['last'])
            
            # 3. Volatility & Strength
            adx = ta.adx(df['high'], df['low'], df['last'], length=adx_len)
            bbands = ta.bbands(df['last'])
            
            # 4. Volume
            df['OBV'] = ta.obv(df['last'], df['volume'])
            
            # รวมข้อมูลทั้งหมด
            full_df = pd.concat([df, macd, adx, bbands], axis=1)
            return full_df.dropna(subset=['SMA_F', 'SMA_S', 'RSI'])
        except: return None

# --- 4. INTERFACE TABS ---
tab1, tab2, tab3 = st.tabs(["🔍 Global Scanner", "🧠 AI Deep Insight", "📊 Sentiment Gauge"])

# --- TAB 1: GLOBAL SCANNER ---
with tab1:
    st.header(f"Multi-Indicator Scanner (Acc: {c_account_no})")
    if st.button("🚀 Start Global Scan"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ กรุณากรอกข้อมูล Settrade ใน Sidebar")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id, 'acc': c_account_no}
            engine = StockAIApp(config)
            
            if engine.market:
                with st.spinner("ประมวลผลข้อมูลทางเทคนิคทั้งระบบ..."):
                    stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                    scan_results = []
                    
                    for s in stocks:
                        df = engine.process_technical_data(s)
                        if df is not None:
                            last = df.iloc[-1]
                            adx_col = f"ADX_{adx_len}"
                            
                            scan_results.append({
                                "Symbol": s,
                                "Price": last['last'],
                                "RSI": round(last['RSI'], 2),
                                "Trend": "📈 Bullish" if last['SMA_F'] > last['SMA_S'] else "📉 Bearish",
                                "Strength (ADX)": round(last[adx_col], 1),
                                "Vol (OBV)": f"{last['OBV']:,.0f}"
                            })
                    
                    if scan_results:
                        st.dataframe(pd.DataFrame(scan_results), use_container_width=True)
                    else:
                        st.error("ไม่พบข้อมูลหลักทรัพย์ โปรดตรวจสอบการเชื่อมต่อ API")

# --- TAB 2: AI INSIGHT (แก้ปัญหา NotFound) ---
with tab2:
    st.header("🧠 30-Day Gemini AI Insight")
    target_stock = st.text_input("ระบุหุ้นที่ต้องการวิเคราะห์", "PTT")
    
    if st.button("🧠 Analyze with AI"):
        if not c_gemini_key:
            st.warning("⚠️ กรุณาใส่ Gemini Key ใน Sidebar")
        else:
            try:
                genai.configure(api_key=c_gemini_key)
                # ค้นหา Model ที่รองรับจริง (Discovery Mode)
                available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                selected_model = ""
                for m_name in ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-pro"]:
                    if m_name in available:
                        selected_model = m_name.replace("models/", "")
                        break
                
                if not selected_model:
                    selected_model = available[0].replace("models/", "") if available else ""

                if selected_model:
                    model = genai.GenerativeModel(selected_model)
                    with st.spinner(f"Gemini ({selected_model}) กำลังเจาะลึกข่าว 30 วัน..."):
                        prompt = f"วิเคราะห์หุ้น {target_stock} ในตลาด SET รอบ 30 วัน: 1.ธุรกิจ 2.ข่าวเด่น 3.Sentiment 4.ความเสี่ยงอาทิตย์หน้า ตอบภาษาไทย"
                        response = model.generate_content(prompt)
                        st.success(f"บทวิเคราะห์โดย {selected_model}")
                        st.markdown(response.text)
                else:
                    st.error("ไม่พบ Model ที่รองรับ")
            except Exception as e:
                st.error(f"AI Error: {e}")

# --- TAB 3: SENTIMENT ---
with tab3:
    st.header("Fear & Greed Dashboard")
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = 65,
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#1f77b4"},
                 'steps' : [{'range': [0, 30], 'color': "#ff4b4b"}, {'range': [70, 100], 'color': "#09ab3b"}]}
    ))
    st.plotly_chart(fig, use_container_width=True)
