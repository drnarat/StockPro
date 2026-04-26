import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings

warnings.filterwarnings('ignore')

# --- 1. UI SETUP ---
st.set_page_config(layout="wide", page_title="SRAN Stock Intelligence v4", page_icon="📈")

# --- 2. SIDEBAR: CREDENTIALS (ใส่ตามที่ดร. แจ้งมาให้ครบ) ---
with st.sidebar:
    st.header("🔑 Settrade Connectivity")
    input_app_id = st.text_input("APP_ID", placeholder="กรอก APP_ID")
    input_app_secret = st.text_input("APP_SECRET", type="password")
    input_app_code = st.text_input("APP_CODE", value="SANDBOX")
    input_broker_id = st.text_input("BROKER_ID", value="SANDBOX")
    input_account_no = st.text_input("ACCOUNT_NO", value="Narats-E")
    
    st.divider()
    st.header("🤖 AI Setting")
    gemini_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.header("⚙️ Indicators Tuning")
    sma_f = st.slider("SMA Fast", 5, 50, 20)
    sma_s = st.slider("SMA Slow", 50, 200, 100)

# --- 3. CORE ENGINE ---
class StockEngine:
    def __init__(self, config):
        try:
            # ใช้ค่าที่ดร. ระบุมาทั้งหมดในการสร้าง Investor
            self.investor = Investor(
                app_id=config['app_id'],
                app_secret=config['app_secret'],
                app_code=config['app_code'],
                broker_id=config['broker_id']
            )
            self.market = self.investor.MarketData()
            # ยืนยันสิทธิ์ในระดับ Equity (ถ้าต้องการเช็คยอดเงินหรือพอร์ตในอนาคต)
            self.equity = self.investor.Equity(account_no=config['account_no'])
            self.account_no = config['account_no']
        except Exception as e:
            st.sidebar.error(f"การเชื่อมต่อล้มเหลว: {e}")
            self.market = None

    def fetch_data(self, symbol):
        try:
            # ดึงข้อมูลย้อนหลัง 250 วัน
            res = self.market.get_candlestick(symbol, "1D", 250)
            df = pd.DataFrame(res)
            if df.empty: return None
            
            # คำนวณอินดิเคเตอร์
            df['SMA_F'] = ta.sma(df['last'], length=sma_f)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s)
            df['RSI'] = ta.rsi(df['last'], length=14)
            df['OBV'] = ta.obv(df['last'], df['volume'])
            
            return df.dropna(subset=['SMA_F', 'SMA_S'])
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Global Scanner", "🧠 AI Deep Insight", "📊 Market Sentiment"])

# --- TAB 1: SCANNER ---
with tab1:
    st.header(f"Market Scanner (Account: {input_account_no})")
    if st.button("🚀 Start Global Scan"):
        if not (input_app_id and input_app_secret):
            st.warning("⚠️ โปรดกรอกข้อมูล API ให้ครบถ้วน")
        else:
            current_config = {
                "app_id": input_app_id, "app_secret": input_app_secret,
                "app_code": input_app_code, "broker_id": input_broker_id,
                "account_no": input_account_no
            }
            engine = StockEngine(current_config)
            
            if engine.market:
                with st.spinner("ประมวลผลข้อมูลตลาด..."):
                    stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                    results = []
                    for s in stocks:
                        df = engine.fetch_data(s)
                        if df is not None:
                            last = df.iloc[-1]
                            results.append({
                                "Symbol": s, "Price": last['last'], "RSI": round(last['RSI'], 2),
                                "Trend": "📈 Bullish" if last['SMA_F'] > last['SMA_S'] else "📉 Bearish",
                                "Volume (OBV)": f"{last['OBV']:,.0f}"
                            })
                    if results: st.dataframe(pd.DataFrame(results), use_container_width=True)
                    else: st.error("ไม่สามารถดึงข้อมูลหุ้นใน List ได้")

# --- TAB 2: AI INSIGHT ---
with tab2:
    st.header("Gemini 30-Day Analysis")
    stock_input = st.text_input("ชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                with st.spinner("AI กำลังวิเคราะห์..."):
                    prompt = f"วิเคราะห์หุ้น {stock_input} ในตลาด SET รอบ 30 วัน: ธุรกิจ, ข่าวเด่น, Sentiment และความเสี่ยง ตอบภาษาไทย"
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
            except Exception as e: st.error(f"AI Error: {e}")
        else: st.warning("ใส่ Gemini API Key ใน Sidebar")

# --- TAB 3: SENTIMENT ---
with tab3:
    st.header("Fear & Greed Index")
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = 65,
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#1f77b4"},
                 'steps' : [{'range': [0, 35], 'color': "#ff4b4b"}, {'range': [65, 100], 'color': "#09ab3b"}]}))
    st.plotly_chart(fig, use_container_width=True)
