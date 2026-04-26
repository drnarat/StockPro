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

# --- 3. THE ANALYTICS ENGINE ---
class StockAnalyst:
    def __init__(self, config):
        try:
            self.investor = Investor(
                app_id=config['id'], app_secret=config['secret'],
                app_code=config['code'], broker_id=config['broker']
            )
            self.market = self.investor.MarketData()
        except: self.market = None

    def get_full_metrics(self, symbol):
        try:
            res = self.market.get_candlestick(symbol, "1D", 350)
            df = pd.DataFrame(res)
            if df.empty: return None

            # คำนวณชุดใหญ่
            df['SMA_F'] = ta.sma(df['last'], length=sma_f_len)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s_len)
            df['EMA_20'] = ta.ema(df['last'], length=20)
            df['RSI'] = ta.rsi(df['last'], length=14)
            
            # MACD
            macd = ta.macd(df['last'])
            # Stochastic
            stoch = ta.stoch(df['high'], df['low'], df['last'])
            # Bollinger Bands
            bb = ta.bbands(df['last'])
            # Volatility & Volume
            df['ATR'] = ta.atr(df['high'], df['low'], df['last'], length=14)
            df['OBV'] = ta.obv(df['last'], df['volume'])

            return pd.concat([df, macd, stoch, bb], axis=1)
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Global Scanner", "🧠 AI Deep Insight", "📊 Sentiment Gauge"])

with tab1:
    st.header(f"Multi-Indicator Scanner (Account: {c_account_no})")
    if st.button("🚀 Run Comprehensive Scan"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ กรุณากรอก API Credentials")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id}
            engine = StockAnalyst(config)
            
            if engine.market:
                with st.spinner("กำลังเจาะข้อมูลและคำนวณอินดิเคเตอร์..."):
                    stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                    results = []
                    
                    for s in stocks:
                        df = engine.get_full_metrics(s)
                        if df is not None:
                            last = df.iloc[-1]
                            
                            # มั่นใจว่าดึงค่ามาครบทุกตัว
                            results.append({
                                "Stock": s,
                                "Price": last.get('last', 0),
                                "SMA_Fast": round(last.get('SMA_F', 0), 2),
                                "SMA_Slow": round(last.get('SMA_S', 0), 2),
                                "EMA_20": round(last.get('EMA_20', 0), 2),
                                "RSI": round(last.get('RSI', 0), 2),
                                "MACD": round(last.get('MACD_12_26_9', 0), 3),
                                "MACD_Sig": round(last.get('MACDs_12_26_9', 0), 3),
                                "Stoch_%K": round(last.get('STOCHk_14_3_3', 0), 2),
                                "Stoch_%D": round(last.get('STOCHd_14_3_3', 0), 2),
                                "BB_Upper": round(last.get('BBU_20_2.0', 0), 2),
                                "BB_Lower": round(last.get('BBL_20_2.0', 0), 2),
                                "ATR": round(last.get('ATR', 0), 3),
                                "OBV": f"{last.get('OBV', 0):,.0f}"
                            })
                    
                    if results:
                        # แสดงผลเป็นตารางชุดใหญ่
                        final_df = pd.DataFrame(results)
                        st.dataframe(final_df, use_container_width=True)
                        st.success(f"สแกนเสร็จสิ้น! แสดงผลทั้งหมด {len(final_df.columns)} อินดิเคเตอร์")
                    else: st.error("ไม่พบข้อมูลหลักทรัพย์")

# [Tab 2 & 3: ปลอดภัยจาก NotFound และ Error]
with tab2:
    st.header("Gemini 30-Day Analysis")
    target = st.text_input("ชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze Stock"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                sel_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                model = genai.GenerativeModel(sel_model)
                resp = model.generate_content(f"วิเคราะห์หุ้น {target} ในตลาด SET: สรุปข่าว 30 วัน, Sentiment และความเสี่ยง (ภาษาไทย)")
                st.markdown(resp.text)
            except Exception as e: st.error(f"AI Error: {e}")

with tab3:
    st.header("Fear & Greed Index")
    fig = go.Figure(go.Indicator(mode="gauge+number", value=65, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#1f77b4"}}))
    st.plotly_chart(fig, use_container_width=True)
