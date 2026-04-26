import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings

warnings.filterwarnings('ignore')

# --- 1. UI SETUP ---
st.set_page_config(layout="wide", page_title="SRAN AI Stock Platform v10", page_icon="📈")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🔑 Connectivity")
    c_app_id = st.text_input("APP_ID")
    c_app_secret = st.text_input("APP_SECRET", type="password")
    c_app_code = st.text_input("APP_CODE", value="SANDBOX")
    c_broker_id = st.text_input("BROKER_ID", value="SANDBOX")
    c_account_no = st.text_input("ACCOUNT_NO", value="Narats-E")
    
    st.divider()
    st.header("⚙️ Indicators Tuning")
    sma_f_len = st.slider("SMA Fast", 5, 50, 20)
    sma_s_len = st.slider("SMA Slow", 50, 200, 100)
    
    st.divider()
    gemini_key = st.text_input("Gemini API Key", type="password")

# --- 3. ANALYTICS ENGINE ---
class FinalEngine:
    def __init__(self, config):
        try:
            self.investor = Investor(app_id=config['id'], app_secret=config['secret'],
                                     app_code=config['code'], broker_id=config['broker'])
            self.market = self.investor.MarketData()
        except: self.market = None

    def get_data(self, symbol):
        try:
            res = self.market.get_candlestick(symbol, "1D", 350)
            df = pd.DataFrame(res)
            if df.empty: return None

            # คำนวณแบบจัดเต็ม
            df['SMA_F'] = ta.sma(df['last'], length=sma_f_len)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s_len)
            df['EMA_20'] = ta.ema(df['last'], length=20)
            df['RSI_VAL'] = ta.rsi(df['last'], length=14)
            df['ATR_VAL'] = ta.atr(df['high'], df['low'], df['last'], length=14)
            df['OBV_VAL'] = ta.obv(df['last'], df['volume'])
            
            # Indicators ที่ได้เป็น DataFrame (MACD, Stoch, BB)
            macd = ta.macd(df['last'])
            stoch = ta.stoch(df['high'], df['low'], df['last'])
            bb = ta.bbands(df['last'])

            return pd.concat([df, macd, stoch, bb], axis=1)
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Market Scanner", "🧠 AI Analysis", "📊 Sentiment Gauge"])

with tab1:
    st.header(f"Full Strategy Scanner (Account: {c_account_no})")
    if st.button("🚀 Start Deep Scan"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ โปรดกรอก API Credentials")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id}
            engine = FinalEngine(config)
            
            if engine.market:
                with st.spinner("กำลังดึงอินดิเคเตอร์ทุกแกน..."):
                    stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                    results = []
                    
                    for s in stocks:
                        df = engine.get_data(s)
                        if df is not None:
                            last = df.iloc[-1]
                            
                            # --- [ WILDCARD MAPPING ] ---
                            # ค้นหาคอลัมน์โดยใช้ Keywords แทนชื่อเต็ม (แก้ปัญหาเรื่องตัวเลข Slider)
                            def find_val(keyword):
                                cols = [c for c in df.columns if keyword in str(c)]
                                return last[cols[0]] if cols else 0

                            results.append({
                                "Stock": s,
                                "Price": last['last'],
                                "SMA_F": round(last['SMA_F'], 2) if not pd.isna(last['SMA_F']) else "N/A",
                                "SMA_S": round(last['SMA_S'], 2) if not pd.isna(last['SMA_S']) else "N/A",
                                "EMA_20": round(last['EMA_20'], 2),
                                "RSI": round(last['RSI_VAL'], 2),
                                "MACD": round(find_val('MACD_'), 3),
                                "MACD_Sig": round(find_val('MACDs_'), 3),
                                "Stoch_%K": round(find_val('STOCHk_'), 2),
                                "Stoch_%D": round(find_val('STOCHd_'), 2),
                                "BB_Upper": round(find_val('BBU_'), 2),
                                "BB_Lower": round(find_val('BBL_'), 2),
                                "ATR": round(last['ATR_VAL'], 3),
                                "Volume (OBV)": f"{last['OBV_VAL']:,.0f}"
                            })
                    
                    if results:
                        st.dataframe(pd.DataFrame(results), use_container_width=True)
                        st.success("✅ แสดงผลครบ 14 คอลัมน์อินดิเคเตอร์")
                    else: st.error("ไม่พบข้อมูลหลักทรัพย์")

# [Tab 2 & 3: Stable Version]
with tab2:
    st.header("Gemini 30-Day Insight")
    target = st.text_input("หุ้น", "PTT")
    if st.button("🧠 Analyze"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                sel_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                model = genai.GenerativeModel(sel_model)
                resp = model.generate_content(f"สรุปหุ้น {target} ตลาด SET: ข่าว 30 วัน, Sentiment, ความเสี่ยง (ไทย)")
                st.markdown(resp.text)
            except Exception as e: st.error(f"AI Error: {e}")

with tab3:
    st.header("Fear & Greed Index")
    fig = go.Figure(go.Indicator(mode="gauge+number", value=65))
    st.plotly_chart(fig, use_container_width=True)
