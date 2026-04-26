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

# --- 3. ANALYTICS ENGINE (Static Column Naming) ---
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

            # สร้าง Dict เพื่อเก็บค่าอินดิเคเตอร์แบบเจาะจงชื่อ
            stats = {}
            stats['Price'] = df['last'].iloc[-1]
            
            # [A] Trend - คำนวณแล้วดึงค่าล่าสุดทันที
            stats['SMA_Fast'] = ta.sma(df['last'], length=sma_f_len).iloc[-1]
            stats['SMA_Slow'] = ta.sma(df['last'], length=sma_s_len).iloc[-1]
            stats['EMA_20'] = ta.ema(df['last'], length=20).iloc[-1]
            
            # [B] Momentum
            stats['RSI'] = ta.rsi(df['last'], length=14).iloc[-1]
            
            macd = ta.macd(df['last'])
            if macd is not None:
                stats['MACD'] = macd.iloc[-1, 0]
                stats['MACD_Sig'] = macd.iloc[-1, 2]
            
            stoch = ta.stoch(df['high'], df['low'], df['last'])
            if stoch is not None:
                stats['Stoch_K'] = stoch.iloc[-1, 0]
                stats['Stoch_D'] = stoch.iloc[-1, 1]
            
            # [C] Volatility & Volume
            bb = ta.bbands(df['last'])
            if bb is not None:
                stats['BB_Upper'] = bb.iloc[-1, 2]
                stats['BB_Lower'] = bb.iloc[-1, 0]
                
            stats['ATR'] = ta.atr(df['high'], df['low'], df['last'], length=14).iloc[-1]
            stats['OBV'] = ta.obv(df['last'], df['volume']).iloc[-1]

            return stats
        except Exception as e:
            return None

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
                with st.spinner("ประมวลผลอินดิเคเตอร์ชุดใหญ่..."):
                    results = []
                    for s in stocks_to_scan:
                        stats = engine.get_indicators(s)
                        if stats:
                            # บังคับโครงสร้างข้อมูลให้มีครบ 14 คอลัมน์
                            row = {"Symbol": s}
                            row.update({k: (round(v, 3) if isinstance(v, (int, float)) and not pd.isna(v) else v) for k, v in stats.items()})
                            results.append(row)
                    
                    if results:
                        final_df = pd.DataFrame(results)
                        # จัดเรียงลำดับคอลัมน์ให้สวยงาม
                        cols_order = ["Symbol", "Price", "SMA_Fast", "SMA_Slow", "EMA_20", "RSI", "MACD", "MACD_Sig", "Stoch_K", "Stoch_D", "BB_Upper", "BB_Lower", "ATR", "OBV"]
                        final_df = final_df.reindex(columns=cols_order)
                        
                        st.dataframe(final_df, use_container_width=True)
                        st.success(f"✅ สำเร็จ: แสดงผลครบทั้ง {len(final_df.columns)} คอลัมน์")
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
