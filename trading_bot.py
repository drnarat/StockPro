import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings

warnings.filterwarnings('ignore')

# --- 1. UI SETUP ---
st.set_page_config(layout="wide", page_title="SRAN Full-Stack Stock AI", page_icon="📈")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🔑 Connectivity")
    c_app_id = st.text_input("APP_ID")
    c_app_secret = st.text_input("APP_SECRET", type="password")
    c_app_code = st.text_input("APP_CODE", value="SANDBOX")
    c_broker_id = st.text_input("BROKER_ID", value="SANDBOX")
    c_account_no = st.text_input("ACCOUNT_NO", value="Narats-E")
    
    st.divider()
    st.header("⚙️ Strategy Parameters")
    sma_f = st.slider("SMA Fast", 5, 50, 20)
    sma_s = st.slider("SMA Slow", 50, 200, 100)
    rsi_p = st.slider("RSI Period", 5, 30, 14)
    
    st.divider()
    gemini_key = st.text_input("Gemini API Key", type="password")

# --- 3. ENGINE ---
class DeepIndicatorEngine:
    def __init__(self, config):
        try:
            self.investor = Investor(
                app_id=config['id'], app_secret=config['secret'],
                app_code=config['code'], broker_id=config['broker']
            )
            self.market = self.investor.MarketData()
        except: self.market = None

    def analyze_full(self, symbol):
        try:
            # ดึงข้อมูลเผื่อไว้ 350 วัน สำหรับอินดิเคเตอร์ระยะยาว
            res = self.market.get_candlestick(symbol, "1D", 350)
            df = pd.DataFrame(res)
            if df.empty: return None

            # [TREND]
            df['SMA_F'] = ta.sma(df['last'], length=sma_f)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s)
            df['EMA_20'] = ta.ema(df['last'], length=20)

            # [MOMENTUM]
            df['RSI'] = ta.rsi(df['last'], length=rsi_p)
            macd = ta.macd(df['last'])
            stoch = ta.stoch(df['high'], df['low'], df['last'])
            
            # [VOLATILITY & VOLUME]
            bbands = ta.bbands(df['last'])
            df['ATR'] = ta.atr(df['high'], df['low'], df['last'], length=14)
            df['OBV'] = ta.obv(df['last'], df['volume'])

            # รวม Indicators ทั้งหมด
            return pd.concat([df, macd, stoch, bbands], axis=1)
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Full Market Scanner", "🧠 AI Strategic Insight", "📊 Sentiment Gauge"])

with tab1:
    st.header(f"Multi-Indicator Deep Scan (Acc: {c_account_no})")
    if st.button("🚀 Start Deep Scan"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ กรุณากรอก API Credentials")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id}
            engine = DeepIndicatorEngine(config)
            
            if engine.market:
                with st.spinner("คำนวณ Indicator ทุกมิติ..."):
                    stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                    results = []
                    
                    for s in stocks:
                        df = engine.analyze_full(s)
                        if df is not None:
                            last = df.iloc[-1]
                            
                            # ดึงชื่อคอลัมน์แบบ Dynamic ป้องกัน Error
                            macd_val = last.get('MACD_12_26_9', 0)
                            stoch_val = last.get('STOCHk_14_3_3', 0)
                            bb_up = last.get('BBU_20_2.0', 0)
                            bb_low = last.get('BBL_20_2.0', 0)

                            results.append({
                                "Symbol": s,
                                "Price": last.get('last', 0),
                                "RSI": round(last.get('RSI', 0), 2) if not pd.isna(last.get('RSI')) else "N/A",
                                "MACD": round(macd_val, 3) if not pd.isna(macd_val) else "N/A",
                                "Stoch %K": round(stoch_val, 2) if not pd.isna(stoch_val) else "N/A",
                                "SMA_F": round(last.get('SMA_F', 0), 2) if not pd.isna(last.get('SMA_F')) else "N/A",
                                "SMA_S": round(last.get('SMA_S', 0), 2) if not pd.isna(last.get('SMA_S')) else "N/A",
                                "EMA_20": round(last.get('EMA_20', 0), 2),
                                "BB Upper": round(bb_up, 2),
                                "BB Lower": round(bb_low, 2),
                                "ATR": round(last.get('ATR', 3), 3),
                                "Volume (OBV)": f"{last.get('OBV', 0):,.0f}"
                            })
                    
                    if results:
                        st.dataframe(pd.DataFrame(results), use_container_width=True)
                    else: st.error("ไม่พบข้อมูลหลักทรัพย์")
            else: st.error("เชื่อมต่อ Settrade ล้มเหลว")

# [Tab 2 & 3 คงเดิมเพื่อความเสถียร]
with tab2:
    st.header("Gemini 30-Day Analysis")
    target = st.text_input("ชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                sel_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                model = genai.GenerativeModel(sel_model)
                resp = model.generate_content(f"วิเคราะห์หุ้น {target} ในตลาด SET รอบ 30 วัน: ธุรกิจ, ข่าวเด่น, Sentiment ตอบภาษาไทย")
                st.markdown(resp.text)
            except Exception as e: st.error(f"AI Error: {e}")

with tab3:
    st.header("Market Sentiment Index")
    fig = go.Figure(go.Indicator(mode="gauge+number", value=65))
    st.plotly_chart(fig, use_container_width=True)
