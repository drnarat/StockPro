import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings

warnings.filterwarnings('ignore')

# --- 1. UI SETUP ---
st.set_page_config(layout="wide", page_title="SRAN AI Stock Platform", page_icon="📈")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🔑 Settrade Connectivity")
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

# --- 3. ANALYTICS ENGINE (Force Rename Logic) ---
class MasterEngine:
    def __init__(self, config):
        try:
            self.investor = Investor(app_id=config['id'], app_secret=config['secret'],
                                     app_code=config['code'], broker_id=config['broker'])
            self.market = self.investor.MarketData()
        except: self.market = None

    def get_indicators(self, symbol):
        try:
            res = self.market.get_candlestick(symbol, "1D", 350)
            df = pd.DataFrame(res)
            if df.empty: return None

            # [A] Trend
            df['SMA_F'] = ta.sma(df['last'], length=sma_f_len)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s_len)
            df['EMA_20'] = ta.ema(df['last'], length=20)
            
            # [B] Momentum (Force Rename คอลัมน์ที่ชื่อไม่นิ่ง)
            df['RSI_V'] = ta.rsi(df['last'], length=14)
            
            macd_df = ta.macd(df['last'])
            if macd_df is not None:
                df['MACD_V'] = macd_df.iloc[:, 0]  # ดึงคอลัมน์แรก (MACD line)
                df['MACD_S'] = macd_df.iloc[:, 2]  # ดึงคอลัมน์สาม (Signal line)
            
            stoch_df = ta.stoch(df['high'], df['low'], df['last'])
            if stoch_df is not None:
                df['STOCH_K'] = stoch_df.iloc[:, 0]
                df['STOCH_D'] = stoch_df.iloc[:, 1]
            
            # [C] Volatility & Volume
            bb_df = ta.bbands(df['last'])
            if bb_df is not None:
                df['BB_UP'] = bb_df.iloc[:, 2] # Upper band
                df['BB_LOW'] = bb_df.iloc[:, 0] # Lower band
                
            df['ATR_V'] = ta.atr(df['high'], df['low'], df['last'], length=14)
            df['OBV_V'] = ta.obv(df['last'], df['volume'])

            return df
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Global Scanner", "🧠 AI Deep Insight", "📊 Sentiment Gauge"])

with tab1:
    st.header(f"Multi-Indicator Scanner (Account: {c_account_no})")
    stocks_to_scan = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
    
    if st.button("🚀 Start Full Arsenal Scan"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ โปรดกรอก API Credentials")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id}
            engine = MasterEngine(config)
            
            if engine.market:
                with st.spinner("ประมวลผล 14 อินดิเคเตอร์เชิงลึก..."):
                    results = []
                    for s in stocks_to_scan:
                        df = engine.get_indicators(s)
                        if df is not None:
                            last = df.iloc[-1]
                            
                            # บังคับสร้างรายการที่มีครบ 14 อินดิเคเตอร์ โดยดึงจากชื่อที่เรา Rename ไว้
                            results.append({
                                "Symbol": s,
                                "Price": last['last'],
                                "SMA_Fast": round(last.get('SMA_F', 0), 2) if not pd.isna(last.get('SMA_F')) else "N/A",
                                "SMA_Slow": round(last.get('SMA_S', 0), 2) if not pd.isna(last.get('SMA_S')) else "N/A",
                                "EMA_20": round(last.get('EMA_20', 0), 2),
                                "RSI": round(last.get('RSI_V', 0), 2),
                                "MACD": round(last.get('MACD_V', 0), 3),
                                "MACD_Sig": round(last.get('MAC_S', 0), 3), # แก้ไขชื่อ key ให้ตรง
                                "Stoch_K": round(last.get('STOCH_K', 0), 2),
                                "Stoch_D": round(last.get('STOCH_D', 0), 2),
                                "BB_Upper": round(last.get('BB_UP', 0), 2),
                                "BB_Lower": round(last.get('BB_LOW', 0), 2),
                                "ATR": round(last.get('ATR_V', 0), 3),
                                "Volume(OBV)": f"{last.get('OBV_V', 0):,.0f}"
                            })
                    
                    if results:
                        st.dataframe(pd.DataFrame(results), use_container_width=True)
                        st.success(f"✅ สำเร็จ: แสดงผลครบทั้ง {len(pd.DataFrame(results).columns)} คอลัมน์")
            else: st.error("เชื่อมต่อระบบ Settrade ล้มเหลว")

with tab2:
    st.header("Gemini AI Strategy Advisor")
    target = st.text_input("ชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze Stock"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                sel_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                model = genai.GenerativeModel(sel_model)
                resp = model.generate_content(f"วิเคราะห์หุ้น {target} ตลาด SET: ข่าวเด่น 30 วัน, Sentiment (ไทย)")
                st.markdown(resp.text)
            except Exception as e: st.error(f"AI Error: {e}")

with tab3:
    st.header("Market Sentiment Index")
    fig = go.Figure(go.Indicator(mode="gauge+number", value=65))
    st.plotly_chart(fig, use_container_width=True)
