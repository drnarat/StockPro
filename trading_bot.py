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

# --- 3. ANALYTICS ENGINE (Safe Data Mapping) ---
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

            # 🛠 สร้าง Dictionary เก็บผลลัพธ์แยกทีละตัว (ป้องกันการพังยกแถว)
            row_data = {"Symbol": symbol, "Price": df['last'].iloc[-1]}
            
            # [1] TREND
            row_data['SMA_Fast'] = ta.sma(df['last'], length=sma_f_len).iloc[-1]
            row_data['SMA_Slow'] = ta.sma(df['last'], length=sma_s_len).iloc[-1]
            row_data['EMA_20'] = ta.ema(df['last'], length=20).iloc[-1]
            
            # [2] MOMENTUM (Safe RSI)
            rsi_s = ta.rsi(df['last'], length=14)
            row_data['RSI'] = rsi_s.iloc[-1] if rsi_s is not None else 0
            
            # [3] MACD (Safe Extraction)
            macd_df = ta.macd(df['last'])
            if macd_df is not None and not macd_df.empty:
                row_data['MACD'] = macd_df.iloc[-1, 0]
                row_data['MACD_Signal'] = macd_df.iloc[-1, 2]
            else:
                row_data['MACD'], row_data['MACD_Signal'] = 0, 0
            
            # [4] Stochastic
            stoch_df = ta.stoch(df['high'], df['low'], df['last'])
            if stoch_df is not None and not stoch_df.empty:
                row_data['Stoch_K'] = stoch_df.iloc[-1, 0]
                row_data['Stoch_D'] = stoch_df.iloc[-1, 1]
            else:
                row_data['Stoch_K'], row_data['Stoch_D'] = 0, 0
            
            # [5] Volatility & Volume
            bb_df = ta.bbands(df['last'])
            if bb_df is not None and not bb_df.empty:
                row_data['BB_Upper'] = bb_df.iloc[-1, 2]
                row_data['BB_Lower'] = bb_df.iloc[-1, 0]
            else:
                row_data['BB_Upper'], row_data['BB_Lower'] = 0, 0
                
            atr_s = ta.atr(df['high'], df['low'], df['last'], length=14)
            row_data['ATR'] = atr_s.iloc[-1] if atr_s is not None else 0
            
            obv_s = ta.obv(df['last'], df['volume'])
            row_data['OBV'] = obv_s.iloc[-1] if obv_s is not None else 0

            return row_data
        except Exception:
            return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Market Scanner", "🧠 AI Strategic Insight", "📊 Market Sentiment"])

with tab1:
    st.header(f"Multi-Indicator Scanner (Account: {c_account_no})")
    st.caption("🚀 **Version: 21.0 (Auditor's Fix)** | Status: Production | Updates: Safe Indicator Mapping")
    
    stocks_list = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
    
    if st.button("🚀 Start Deep Scan (Restore 14 Indicators)"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ โปรดกรอก API Credentials ที่ Sidebar")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id}
            engine = MasterEngine(config)
            
            if engine.market:
                with st.spinner("กำลังเจาะระบบข้อมูลและประมวลผลอินดิเคเตอร์..."):
                    all_results = []
                    for s in stocks_list:
                        ind_data = engine.get_indicators(s)
                        if ind_data:
                            # ปรับทศนิยมให้สะอาดตา
                            clean_row = {}
                            for k, v in ind_data.items():
                                if isinstance(v, (int, float)) and not pd.isna(v):
                                    clean_row[k] = f"{v:,.2f}" if k != "OBV" else f"{v:,.0f}"
                                else:
                                    clean_row[k] = v
                            all_results.append(clean_row)
                    
                    if all_results:
                        final_df = pd.DataFrame(all_results)
                        # จัดลำดับคอลัมน์ให้แน่นอน
                        cols = ["Symbol", "Price", "SMA_Fast", "SMA_Slow", "EMA_20", "RSI", "MACD", "MACD_Signal", "Stoch_K", "Stoch_D", "BB_Upper", "BB_Lower", "ATR", "OBV"]
                        st.dataframe(final_df.reindex(columns=cols), use_container_width=True)
                        st.success(f"✅ สำเร็จ: พบข้อมูลครบ {len(final_df.columns)} คอลัมน์")
            else: st.error("❌ เชื่อมต่อระบบ Settrade ล้มเหลว")

# [Tab 2 & 3 คงที่เพื่อความเสถียร]
with tab2:
    st.header("Gemini AI Strategic Insight")
    target = st.text_input("ชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                sel_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                model = genai.GenerativeModel(sel_model)
                resp = model.generate_content(f"สรุปหุ้น {target} ตลาด SET: ข่าว 30 วัน, Sentiment (ตอบภาษาไทย)")
                st.markdown(resp.text)
            except Exception as e: st.error(f"AI Error: {e}")

with tab3:
    st.header("Fear & Greed Index")
    fig = go.Figure(go.Indicator(mode="gauge+number", value=65))
    st.plotly_chart(fig, use_container_width=True)
