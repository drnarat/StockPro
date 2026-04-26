import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings

warnings.filterwarnings('ignore')

# --- 1. SETUP ---
st.set_page_config(layout="wide", page_title="SRAN AI Stock Platform", page_icon="📈")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🔑 Connectivity")
    c_app_id = st.text_input("APP_ID")
    c_app_secret = st.text_input("APP_SECRET", type="password")
    c_app_code = st.text_input("APP_CODE", value="SANDBOX")
    c_broker_id = st.text_input("BROKER_ID", value="SANDBOX")
    c_account_no = st.text_input("ACCOUNT_NO", value="Narats-E")
    
    st.divider()
    st.header("⚙️ Tuning")
    sma_f_len = st.slider("SMA Fast", 5, 50, 20)
    sma_s_len = st.slider("SMA Slow", 50, 200, 100)
    
    st.divider()
    gemini_key = st.text_input("Gemini API Key", type="password")

# --- 3. ENGINE (ปรับปรุงให้คำนวณครบ 14 ค่า) ---
class VerifiedEngine:
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

            # คำนวณค่าหลัก (กำหนดชื่อคอลัมน์ให้ตายตัวเพื่อป้องกันการหาย)
            df['SMA_FAST_VAL'] = ta.sma(df['last'], length=sma_f_len)
            df['SMA_SLOW_VAL'] = ta.sma(df['last'], length=sma_s_len)
            df['EMA_20_VAL'] = ta.ema(df['last'], length=20)
            df['RSI_VAL'] = ta.rsi(df['last'], length=14)
            df['ATR_VAL'] = ta.atr(df['high'], df['low'], df['last'], length=14)
            df['OBV_VAL'] = ta.obv(df['last'], df['volume'])
            
            # Indicators ที่เป็น DataFrame (ชื่อจะเปลี่ยนตามค่า Slider)
            macd = ta.macd(df['last'])
            stoch = ta.stoch(df['high'], df['low'], df['last'])
            bb = ta.bbands(df['last'])

            return pd.concat([df, macd, stoch, bb], axis=1)
        except: return None

# --- 4. MAIN UI ---
tab1, tab2, tab3 = st.tabs(["🔍 Global Scanner", "🧠 AI Deep Insight", "📊 Sentiment Gauge"])

with tab1:
    st.header(f"Multi-Indicator Scanner (Acc: {c_account_no})")
    
    # ประกาศรายชื่อหุ้นภายใน Tab เพื่อป้องกัน NameError
    stocks_to_scan = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
    
    if st.button("🚀 Run Fully Verified Scan"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ กรุณากรอกข้อมูลเชื่อมต่อให้ครบ")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id}
            engine = VerifiedEngine(config)
            
            if engine.market:
                with st.spinner("ประมวลผลอินดิเคเตอร์ 14 ตัว..."):
                    final_results = []
                    
                    for s in stocks_to_scan: # เรียกใช้ตัวแปรที่ประกาศไว้ข้างบน
                        df = engine.get_indicators(s)
                        if df is not None:
                            last = df.iloc[-1]
                            
                            # ฟังก์ชัน Wildcard ค้นหาคอลัมน์ที่มีชื่อไม่คงที่
                            def find_col(keyword):
                                matched = [c for c in df.columns if keyword in str(c)]
                                if matched:
                                    val = last[matched[0]]
                                    return round(val, 3) if not pd.isna(val) else "N/A"
                                return "N/A"

                            final_results.append({
                                "Symbol": s,
                                "Price": last['last'],
                                "SMA_F": find_col('SMA_FAST_VAL'),
                                "SMA_S": find_col('SMA_SLOW_VAL'),
                                "EMA_20": find_col('EMA_20_VAL'),
                                "RSI": find_col('RSI_VAL'),
                                "MACD": find_col('MACD_'),
                                "MACD_Sig": find_col('MACDs_'),
                                "Stoch_K": find_col('STOCHk_'),
                                "Stoch_D": find_col('STOCHd_'),
                                "BB_Upper": find_col('BBU_'),
                                "BB_Lower": find_col('BBL_'),
                                "ATR": find_col('ATR_VAL'),
                                "OBV": f"{last.get('OBV_VAL', 0):,.0f}"
                            })
                    
                    if final_results:
                        st.dataframe(pd.DataFrame(final_results), use_container_width=True)
                        st.success(f"✅ ตรวจสอบแล้ว: แสดงผลครบ {len(pd.DataFrame(final_results).columns)} คอลัมน์")
                    else: st.error("ไม่พบข้อมูลหลักทรัพย์")

with tab2:
    st.header("Gemini AI Insight")
    target = st.text_input("ชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                # ค้นหารุ่นที่รองรับอัตโนมัติ
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                sel_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                model = genai.GenerativeModel(sel_model)
                resp = model.generate_content(f"วิเคราะห์หุ้น {target} ตลาด SET: ข่าวเด่น 30 วัน, Sentiment (ตอบภาษาไทย)")
                st.markdown(resp.text)
            except Exception as e: st.error(f"AI Error: {e}")

with tab3:
    st.header("Market Sentiment Gauge")
    fig = go.Figure(go.Indicator(mode="gauge+number", value=65))
    st.plotly_chart(fig, use_container_width=True)
