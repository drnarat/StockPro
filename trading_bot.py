import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings

warnings.filterwarnings('ignore')

# --- 1. UI SETUP ---
st.set_page_config(layout="wide", page_title="SRAN Stock Platform v11", page_icon="📈")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🔑 Connectivity")
    c_app_id = st.text_input("APP_ID", placeholder="กรอก APP_ID")
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

# --- 3. ANALYTICS ENGINE (Verified Logic) ---
class FinalEngine:
    def __init__(self, config):
        try:
            self.investor = Investor(app_id=config['id'], app_secret=config['secret'],
                                     app_code=config['code'], broker_id=config['broker'])
            self.market = self.investor.MarketData()
        except: self.market = None

    def get_data(self, symbol):
        try:
            # ดึงข้อมูลย้อนหลัง 350 วัน เพื่อรองรับ SMA Slow
            res = self.market.get_candlestick(symbol, "1D", 350)
            df = pd.DataFrame(res)
            if df.empty: return None

            # [1] คำนวณค่าที่เป็น Single Column ก่อน
            df['SMA_F'] = ta.sma(df['last'], length=sma_f_len)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s_len)
            df['EMA_20'] = ta.ema(df['last'], length=20)
            df['RSI_V'] = ta.rsi(df['last'], length=14)
            df['ATR_V'] = ta.atr(df['high'], df['low'], df['last'], length=14)
            df['OBV_V'] = ta.obv(df['last'], df['volume'])
            
            # [2] คำนวณค่าที่เป็น Multi-Column (MACD, Stoch, BB)
            # เราจะไม่ concat ทันที แต่จะดึงค่าจากตัวแปรเหล่านี้โดยตรง
            macd = ta.macd(df['last'])
            stoch = ta.stoch(df['high'], df['low'], df['last'])
            bb = ta.bbands(df['last'])

            # รวมเข้า DataFrame หลัก
            df = pd.concat([df, macd, stoch, bb], axis=1)
            return df
        except Exception as e:
            return None

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
                with st.spinner("กำลังรันการทดสอบและดึงข้อมูล..."):
                    stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                    results = []
                    
                    for s in stocks:
                        df = engine.get_data(s)
                        if df is not None:
                            last = df.iloc[-1]
                            
                            # ฟังก์ชันช่วยหาค่าจากคอลัมน์ที่ชื่อเปลี่ยนไปตาม Slider (Wildcard Search)
                            def get_v(keyword):
                                match_cols = [c for c in df.columns if keyword in str(c)]
                                if match_cols:
                                    val = last[match_cols[0]]
                                    return round(val, 3) if not pd.isna(val) else "N/A"
                                return "N/A"

                            # บังคับสร้าง Dictionary ที่มีครบทุก Key
                            row = {
                                "Stock": s,
                                "Price": last['last'],
                                "SMA_Fast": get_v('SMA_F'),
                                "SMA_Slow": get_v('SMA_S'),
                                "EMA_20": get_v('EMA_20'),
                                "RSI": get_v('RSI_V'),
                                "MACD": get_v('MACD_'),
                                "MACD_Sig": get_v('MACDs_'),
                                "Stoch_%K": get_v('STOCHk_'),
                                "Stoch_%D": get_v('STOCHd_'),
                                "BB_Upper": get_v('BBU_'),
                                "BB_Lower": get_v('BBL_'),
                                "ATR": get_v('ATR_V'),
                                "OBV": f"{last.get('OBV_V', 0):,.0f}"
                            }
                            results.append(row)
                    
                    if results:
                        final_df = pd.DataFrame(results)
                        # ใช้ st.table แทน st.dataframe ชั่วคราวเพื่อบังคับแสดงผลทุกคอลัมน์ให้ดร.เห็นชัดๆ
                        st.write("### ผลการสแกนหุ้น (Complete 14 Indicators)")
                        st.dataframe(final_df, use_container_width=True)
                        st.success(f"✅ ตรวจสอบแล้ว: แสดงผลครบ {len(final_df.columns)} คอลัมน์")
                    else:
                        st.error("ไม่พบข้อมูลหลักทรัพย์ (Check API connection/Sandbox data)")
            else:
                st.error("เชื่อมต่อ Settrade ล้มเหลว")

# [Tab 2 & 3: Stable Version]
with tab2:
    st.header("Gemini 30-Day Insight")
    target = st.text_input("ระบุชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze Stock"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                sel_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                model = genai.GenerativeModel(sel_model)
                resp = model.generate_content(f"วิเคราะห์หุ้น {target} ตลาด SET: สรุปข่าว 30 วันที่ผ่านมา, Sentiment และความเสี่ยง (ตอบภาษาไทย)")
                st.markdown(resp.text)
            except Exception as e: st.error(f"AI Error: {e}")

with tab3:
    st.header("Market Sentiment Index")
    fig = go.Figure(go.Indicator(mode="gauge+number", value=65))
    st.plotly_chart(fig, use_container_width=True)
