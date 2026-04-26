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

# --- 2. SIDEBAR: FULL PARAMETERS ---
with st.sidebar:
    st.header("🔑 Settrade API")
    app_id = st.text_input("APP_ID")
    app_secret = st.text_input("APP_SECRET", type="password")
    app_code = st.text_input("APP_CODE", value="SANDBOX")
    broker_id = st.text_input("BROKER_ID", value="SANDBOX")
    account_no = st.text_input("ACCOUNT_NO", value="Narats-E")
    
    st.divider()
    st.header("⚙️ Advanced Tuning")
    
    with st.expander("📈 Moving Averages (Trend)", expanded=True):
        sma_f = st.slider("SMA Fast", 5, 50, 20)
        sma_s = st.slider("SMA Slow", 50, 200, 100)
        ema_len = st.slider("EMA Period", 5, 50, 9)

    with st.expander("🚀 Momentum (RSI/MACD/Stoch)"):
        rsi_len = st.slider("RSI Period", 5, 30, 14)
        macd_f = st.number_input("MACD Fast", 12)
        macd_s = st.number_input("MACD Slow", 26)
        stoch_k = st.slider("Stochastic %K", 5, 30, 14)

    with st.expander("🌪 Volatility & Volume"):
        bb_len = st.slider("Bollinger Period", 10, 50, 20)
        atr_len = st.slider("ATR (Volatility)", 5, 30, 14)

    st.divider()
    gemini_key = st.text_input("Gemini API Key", type="password")

# --- 3. THE ANALYTICS ENGINE ---
class FullIndicatorEngine:
    def __init__(self, config):
        try:
            self.investor = Investor(
                app_id=config['app_id'], app_secret=config['app_secret'],
                app_code=config['app_code'], broker_id=config['broker_id']
            )
            self.market = self.investor.MarketData()
        except: self.market = None

    def calculate_all(self, symbol):
        try:
            res = self.market.get_candlestick(symbol, "1D", 250)
            df = pd.DataFrame(res)
            if df.empty: return None

            # --- [ Trend ] ---
            df['SMA_F'] = ta.sma(df['last'], length=sma_f)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s)
            df['EMA'] = ta.ema(df['last'], length=ema_len)

            # --- [ Momentum ] ---
            df['RSI'] = ta.rsi(df['last'], length=rsi_len)
            macd = ta.macd(df['last'], fast=macd_f, slow=macd_s)
            stoch = ta.stoch(df['high'], df['low'], df['last'], k=stoch_k)

            # --- [ Volatility ] ---
            bbands = ta.bbands(df['last'], length=bb_len)
            df['ATR'] = ta.atr(df['high'], df['low'], df['last'], length=atr_len)

            # --- [ Volume ] ---
            df['OBV'] = ta.obv(df['last'], df['volume'])

            return pd.concat([df, macd, stoch, bbands], axis=1).dropna(subset=['SMA_S', 'RSI'])
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Full Market Scanner", "🧠 30-Day AI Insight", "📊 Market Sentiment"])

with tab1:
    st.header(f"Multi-Indicator Scanner (Account: {account_no})")
    if st.button("🚀 Start Global Scan"):
        config = {"app_id": app_id, "app_secret": app_secret, "app_code": app_code, "broker_id": broker_id, "account_no": account_no}
        engine = FullIndicatorEngine(config)
        
        if engine.market:
            with st.spinner("ประมวลผลอินดิเคเตอร์ทุกแกนวิเคราะห์..."):
                stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                results = []
                for s in stocks:
                    df = engine.calculate_all(s)
                    if df is not None:
                        last = df.iloc[-1]
                        # ดึงชื่อคอลัมน์ MACD และ Stoch ที่ Dynamic ตามค่าที่เราตั้ง
                        macd_col = [c for c in df.columns if 'MACD_' in c][0]
                        stoch_col = [c for c in df.columns if 'STOCHk_' in c][0]
                        
                        results.append({
                            "Symbol": s,
                            "Price": last['last'],
                            "RSI": round(last['RSI'], 2),
                            "MACD": round(last[macd_col], 2),
                            "Stoch %K": round(last[stoch_col], 2),
                            "SMA_F/S": f"{round(last['SMA_F'],1)} / {round(last['SMA_S'],1)}",
                            "EMA": round(last['EMA'], 2),
                            "ATR": round(last['ATR'], 2),
                            "OBV": f"{last['OBV']:,.0f}",
                            "Trend": "📈 Bullish" if last['SMA_F'] > last['SMA_S'] else "📉 Bearish"
                        })
                if results: st.dataframe(pd.DataFrame(results), use_container_width=True)
                else: st.error("ไม่สามารถดึงข้อมูลได้ โปรดเช็ค API")
        else: st.info("กรุณากรอกข้อมูลการเชื่อมต่อที่ Sidebar")

# --- Tab 2 & 3 (โค้ด AI และ Sentiment เหมือนเดิมเพื่อความเสถียร) ---
with tab2:
    st.header("Gemini 30-Day Analysis")
    target = st.text_input("ชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze"):
        if gemini_key:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            with st.spinner("AI กำลังวิเคราะห์..."):
                resp = model.generate_content(f"วิเคราะห์หุ้น {target} ในตลาด SET รอบ 30 วัน: ธุรกิจ, ข่าวเด่น, Sentiment และความเสี่ยง ตอบภาษาไทย")
                st.markdown(resp.text)
        else: st.warning("ใส่ Gemini API Key ใน Sidebar")

with tab3:
    st.header("Fear & Greed Index")
    fig = go.Figure(go.Indicator(mode = "gauge+number", value = 65, gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#1f77b4"}}))
    st.plotly_chart(fig, use_container_width=True)
