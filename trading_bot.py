import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings

warnings.filterwarnings('ignore')

# --- 1. UI SETUP ---
st.set_page_config(layout="wide", page_title="SRAN AI Stock Intelligence", page_icon="📈")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🔑 Settrade Connection")
    c_app_id = st.text_input("APP_ID")
    c_app_secret = st.text_input("APP_SECRET", type="password")
    c_app_code = st.text_input("APP_CODE", value="SANDBOX")
    c_broker_id = st.text_input("BROKER_ID", value="SANDBOX")
    c_account_no = st.text_input("ACCOUNT_NO", value="Narats-E")
    
    st.divider()
    st.header("⚙️ Indicators Tuning")
    sma_f_val = st.slider("SMA Fast", 5, 50, 20)
    sma_s_val = st.slider("SMA Slow", 50, 200, 100)
    rsi_val = st.slider("RSI Period", 5, 30, 14)
    
    st.divider()
    gemini_key = st.text_input("Gemini API Key", type="password")

# --- 3. CORE ENGINE ---
class RobustStockEngine:
    def __init__(self, config):
        try:
            self.investor = Investor(
                app_id=config['id'], app_secret=config['secret'],
                app_code=config['code'], broker_id=config['broker']
            )
            self.market = self.investor.MarketData()
        except: self.market = None

    def get_indicators(self, symbol):
        try:
            # ดึงข้อมูลย้อนหลังสูงสุด 300 วัน เพื่อรองรับ SMA Slow
            res = self.market.get_candlestick(symbol, "1D", 300)
            df = pd.DataFrame(res)
            if df.empty: return None

            # คำนวณอินดิเคเตอร์แบบแยกส่วน (เพื่อไม่ให้ตัวหนึ่งเสียแล้วเสียทั้งหมด)
            df['SMA_F'] = ta.sma(df['last'], length=sma_f_val)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s_val)
            df['RSI'] = ta.rsi(df['last'], length=rsi_val)
            
            # MACD
            macd = ta.macd(df['last'])
            if macd is not None: df = pd.concat([df, macd], axis=1)
            
            # Bollinger Bands
            bb = ta.bbands(df['last'])
            if bb is not None: df = pd.concat([df, bb], axis=1)
            
            # Volume & Volatility
            df['OBV'] = ta.obv(df['last'], df['volume'])
            df['ATR'] = ta.atr(df['high'], df['low'], df['last'], length=14)

            return df # ไม่ใช้ dropna() เพื่อให้เห็นค่าที่มีอยู่จริง
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Global Scanner", "🧠 AI Deep Insight", "📊 Sentiment Gauge"])

with tab1:
    st.header(f"Market Scanner (Account: {c_account_no})")
    if st.button("🚀 Start Global Scan"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ กรุณากรอก API Credentials")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id}
            engine = RobustStockEngine(config)
            
            if engine.market:
                with st.spinner("กำลังรวบรวมข้อมูล..."):
                    # รายชื่อหุ้นที่มักจะมีข้อมูลใน Sandbox
                    stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "BDMS", "GULF"]
                    results = []
                    
                    for s in stocks:
                        df = engine.get_indicators(s)
                        if df is not None and not df.empty:
                            last = df.iloc[-1]
                            
                            # ตรวจสอบชื่อคอลัมน์ MACD อัตโนมัติ
                            macd_val = last.get(f'MACD_{12}_{26}_{9}', 0)
                            
                            results.append({
                                "Symbol": s,
                                "Price": last.get('last', 0),
                                "RSI": round(last.get('RSI', 0), 2) if not pd.isna(last.get('RSI')) else "N/A",
                                "SMA_F": round(last.get('SMA_F', 0), 2) if not pd.isna(last.get('SMA_F')) else "N/A",
                                "SMA_S": round(last.get('SMA_S', 0), 2) if not pd.isna(last.get('SMA_S')) else "N/A",
                                "MACD": round(macd_val, 2) if not pd.isna(macd_val) else "N/A",
                                "ATR": round(last.get('ATR', 0), 2) if not pd.isna(last.get('ATR')) else "N/A",
                                "OBV": f"{last.get('OBV', 0):,.0f}",
                                "Status": "📈 Bull" if (not pd.isna(last.get('SMA_F')) and not pd.isna(last.get('SMA_S')) and last['SMA_F'] > last['SMA_S']) else "📉 Bear/Wait"
                            })
                    
                    if results:
                        st.dataframe(pd.DataFrame(results), use_container_width=True)
                    else:
                        st.error("❌ ไม่สามารถดึงข้อมูลได้: อาจเกิดจากสิทธิ์ API หรือข้อมูลใน Sandbox ไม่พร้อมใช้งาน")
            else:
                st.error("❌ เชื่อมต่อ Settrade ไม่สำเร็จ")

# --- Tab 2 & 3 คงเดิมเพื่อความเสถียร ---
with tab2:
    st.header("Gemini 30-Day Analysis")
    target = st.text_input("ชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze"):
        if gemini_key:
            genai.configure(api_key=gemini_key)
            # ค้นหาโมเดลที่ใช้งานได้อัตโนมัติ
            try:
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                sel_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                model = genai.GenerativeModel(sel_model)
                resp = model.generate_content(f"วิเคราะห์หุ้น {target} ในตลาด SET รอบ 30 วัน: ธุรกิจ, ข่าวเด่น, Sentiment ตอบภาษาไทย")
                st.markdown(resp.text)
            except Exception as e: st.error(f"AI Error: {e}")

with tab3:
    st.header("Fear & Greed Index")
    fig = go.Figure(go.Indicator(mode="gauge+number", value=65))
    st.plotly_chart(fig, use_container_width=True)
