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
    st.header("🔑 Settrade Connectivity")
    c_app_id = st.text_input("APP_ID", placeholder="ระบุ APP_ID")
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

# --- 3. ANALYTICS ENGINE (Index-Based Extraction) ---
class MasterEngine:
    def __init__(self, config):
        try:
            self.investor = Investor(app_id=config['id'], app_secret=config['secret'],
                                     app_code=config['code'], broker_id=config['broker'])
            self.market = self.investor.MarketData()
        except: self.market = None

    def get_indicators(self, symbol):
        try:
            # ดึงข้อมูลย้อนหลัง 350 วัน
            res = self.market.get_candlestick(symbol, "1D", 350)
            df = pd.DataFrame(res)
            if df.empty: return None

            # [A] สร้าง DataFrame ใหม่เพื่อเก็บเฉพาะอินดิเคเตอร์ที่เราจะใช้
            tech = pd.DataFrame(index=df.index)
            tech['Price'] = df['last']
            
            # [B] คำนวณทีละตัวและตั้งชื่อให้ "นิ่ง" (Fixed Names)
            tech['SMA_Fast'] = ta.sma(df['last'], length=sma_f_len)
            tech['SMA_Slow'] = ta.sma(df['last'], length=sma_s_len)
            tech['EMA_20'] = ta.ema(df['last'], length=20)
            tech['RSI'] = ta.rsi(df['last'], length=14)
            
            # MACD (ดึงจาก Series)
            macd_raw = ta.macd(df['last'])
            if macd_raw is not None:
                tech['MACD'] = macd_raw.iloc[:, 0]
                tech['MACD_Sig'] = macd_raw.iloc[:, 2]
            
            # Stochastic
            stoch_raw = ta.stoch(df['high'], df['low'], df['last'])
            if stoch_raw is not None:
                tech['Stoch_K'] = stoch_raw.iloc[:, 0]
                tech['Stoch_D'] = stoch_raw.iloc[:, 1]
            
            # Bollinger Bands
            bb_raw = ta.bbands(df['last'])
            if bb_raw is not None:
                tech['BB_Upper'] = bb_raw.iloc[:, 2]
                tech['BB_Lower'] = bb_raw.iloc[:, 0]
                
            tech['ATR'] = ta.atr(df['high'], df['low'], df['last'], length=14)
            tech['OBV'] = ta.obv(df['last'], df['volume'])

            return tech.dropna(subset=['Price'])
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Global Scanner", "🧠 AI Deep Insight", "📊 Sentiment Gauge"])

with tab1:
    st.header(f"Multi-Indicator Scanner (Account: {c_account_no})")
    stocks_to_scan = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
    
    if st.button("🚀 Start Deep Scan"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ กรุณากรอก API Credentials")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id}
            engine = MasterEngine(config)
            
            if engine.market:
                with st.spinner("ประมวลผล 14 อินดิเคเตอร์เชิงลึก..."):
                    results = []
                    for s in stocks_to_scan:
                        tech_df = engine.get_indicators(s)
                        if tech_df is not None:
                            last = tech_df.iloc[-1]
                            
                            # บังคับดึงค่าตามชื่อที่เราตั้งไว้ (Fixed Mapping)
                            results.append({
                                "Symbol": s,
                                "Price": last['Price'],
                                "SMA_Fast": round(last.get('SMA_Fast', 0), 2),
                                "SMA_Slow": round(last.get('SMA_Slow', 0), 2),
                                "EMA_20": round(last.get('EMA_20', 0), 2),
                                "RSI": round(last.get('RSI', 0), 2),
                                "MACD": round(last.get('MACD', 0), 3),
                                "MACD_Sig": round(last.get('MACD_Sig', 0), 3),
                                "Stoch_K": round(last.get('Stoch_K', 0), 2),
                                "Stoch_D": round(last.get('Stoch_D', 0), 2),
                                "BB_Upper": round(last.get('BB_Upper', 0), 2),
                                "BB_Lower": round(last.get('BB_Lower', 0), 2),
                                "ATR": round(last.get('ATR', 0), 3),
                                "Volume(OBV)": f"{last.get('OBV', 0):,.0f}"
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
