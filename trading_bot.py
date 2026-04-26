import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings

# ปรับปรุงให้ระบบเสถียรและสะอาดที่สุด
warnings.filterwarnings('ignore')

# --- 1. CONFIGURATION ---
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

# --- 3. CORE ANALYTICS ENGINE ---
class RobustEngine:
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

            # [TREND]
            df['SMA_F'] = ta.sma(df['last'], length=sma_f_len)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s_len)
            df['EMA_20'] = ta.ema(df['last'], length=20)
            
            # [MOMENTUM]
            df['RSI_V'] = ta.rsi(df['last'], length=14)
            macd = ta.macd(df['last'])
            stoch = ta.stoch(df['high'], df['low'], df['last'])
            
            # [VOLATILITY & VOLUME]
            bb = ta.bbands(df['last'])
            df['ATR_V'] = ta.atr(df['high'], df['low'], df['last'], length=14)
            df['OBV_V'] = ta.obv(df['last'], df['volume'])

            # รวมผลลัพธ์
            return pd.concat([df, macd, stoch, bb], axis=1)
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Global Scanner", "🧠 AI Deep Analysis", "📊 Sentiment Gauge"])

with tab1:
    st.header(f"Multi-Indicator Scanner (Acc: {c_account_no})")
    
    # ประกาศรายชื่อหุ้นภายใน Tab
    stocks_to_scan = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
    
    if st.button("🚀 Start Deep Scan"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ กรุณากรอก APP_ID และ APP_SECRET")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id}
            engine = RobustEngine(config)
            
            if engine.market:
                with st.spinner("คำนวณ 14 อินดิเคเตอร์เชิงลึก..."):
                    scan_results = []
                    
                    for s in stocks_to_scan:
                        df = engine.get_indicators(s)
                        if df is not None:
                            last = df.iloc[-1]
                            
                            # ฟังก์ชันหาค่าจาก Column Name ที่ชื่อไม่คงที่
                            def get_indicator_val(keyword):
                                cols = [c for c in df.columns if keyword in str(c)]
                                if cols:
                                    val = last[cols[0]]
                                    return round(val, 3) if not pd.isna(val) else "N/A"
                                return "N/A"

                            # สร้างแถวข้อมูลแบบมาตรฐาน (Standard Dictionary)
                            scan_results.append({
                                "Symbol": s,
                                "Price": last['last'],
                                "SMA_Fast": get_indicator_val('SMA_F'),
                                "SMA_Slow": get_indicator_val('SMA_S'),
                                "EMA_20": get_indicator_val('EMA_20'),
                                "RSI": get_indicator_val('RSI_V'),
                                "MACD": get_indicator_val('MACD_'),
                                "MACD_Sig": get_indicator_val('MACDs_'),
                                "Stoch_K": get_indicator_val('STOCHk_'),
                                "Stoch_D": get_indicator_val('STOCHd_'),
                                "BB_Upper": get_indicator_val('BBU_'),
                                "BB_Lower": get_indicator_val('BBL_'),
                                "ATR": get_indicator_val('ATR_V'),
                                "Volume(OBV)": f"{last.get('OBV_V', 0):,.0f}"
                            })
                    
                    if scan_results:
                        st.dataframe(pd.DataFrame(scan_results), use_container_width=True)
                        st.success(f"✅ ประมวลผลสำเร็จ: ตรวจพบ {len(pd.DataFrame(scan_results).columns)} คอลัมน์")
                    else:
                        st.error("ไม่พบข้อมูลหลักทรัพย์")
            else:
                st.error("เชื่อมต่อระบบ Settrade ล้มเหลว")

with tab2:
    st.header("Gemini AI Strategy Advisor")
    target_stock = st.text_input("ชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze Stock"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                sel_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                model = genai.GenerativeModel(sel_model)
                resp = model.generate_content(f"วิเคราะห์หุ้น {target_stock} ตลาด SET: ข่าวเด่น 30 วัน, Sentiment (ไทย)")
                st.markdown(resp.text)
            except Exception as e: st.error(f"AI Error: {e}")

with tab3:
    st.header("Fear & Greed Index")
    fig = go.Figure(go.Indicator(mode="gauge+number", value=65))
    st.plotly_chart(fig, use_container_width=True)
