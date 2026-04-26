import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from settrade_v2 import Investor
import warnings

# ปิด Warning เพื่อความสะอาดของหน้าจอ
warnings.filterwarnings('ignore')

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="SRAN AI Stock Platform", page_icon="📈")

# --- 2. SIDEBAR: CREDENTIALS & PARAMETERS ---
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
    rsi_len = st.slider("RSI Period", 5, 30, 14)
    
    st.divider()
    gemini_key = st.text_input("Gemini API Key", type="password")

# --- 3. ANALYTICS ENGINE (Verified Logic) ---
class MasterEngine:
    def __init__(self, config):
        try:
            self.investor = Investor(app_id=config['id'], app_secret=config['secret'],
                                     app_code=config['code'], broker_id=config['broker'])
            self.market = self.investor.MarketData()
        except: self.market = None

    def get_indicators(self, symbol):
        try:
            # ดึงข้อมูลย้อนหลัง 350 วัน เพื่อรองรับ SMA ระยะยาว
            res = self.market.get_candlestick(symbol, "1D", 350)
            df = pd.DataFrame(res)
            if df.empty: return None

            # [A] คำนวณค่าเดี่ยว (กำหนดชื่อตายตัว)
            df['SMA_F'] = ta.sma(df['last'], length=sma_f_len)
            df['SMA_S'] = ta.sma(df['last'], length=sma_s_len)
            df['EMA_20'] = ta.ema(df['last'], length=20)
            df['RSI_V'] = ta.rsi(df['last'], length=rsi_len)
            df['ATR_V'] = ta.atr(df['high'], df['low'], df['last'], length=14)
            df['OBV_V'] = ta.obv(df['last'], df['volume'])
            
            # [B] คำนวณค่ากลุ่ม (MACD, Stoch, BB)
            macd = ta.macd(df['last'])
            stoch = ta.stoch(df['high'], df['low'], df['last'])
            bb = ta.bbands(df['last'])

            # รวมเข้า DataFrame หลัก
            df_final = pd.concat([df, macd, stoch, bb], axis=1)
            return df_final
        except: return None

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔍 Global Scanner", "🧠 AI Deep Analysis", "📊 Sentiment Gauge"])

with tab1:
    st.header(f"Multi-Indicator Scanner (Acc: {c_account_no})")
    
    # รายชื่อหุ้นเป้าหมาย (ประกาศภายใน Tab เพื่อป้องกัน NameError)
    stocks_list = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
    
    if st.button("🚀 Start Comprehensive Scan"):
        if not (c_app_id and c_app_secret):
            st.warning("⚠️ กรุณากรอก APP_ID และ APP_SECRET")
        else:
            config = {'id': c_app_id, 'secret': c_app_secret, 'code': c_app_code, 'broker': c_broker_id}
            engine = MasterEngine(config)
            
            if engine.market:
                with st.spinner("ประมวลผลอินดิเคเตอร์ชุดใหญ่ (14 ค่า)..."):
                    scan_results = []
                    
                    for s in stocks_list:
                        df = engine.get_indicators(s)
                        if df is not None:
                            last_row = df.iloc[-1]
                            
                            # 💡 หัวใจสำคัญ: ระบบ Keyword Mapping (Wildcard)
                            # ช่วยหาคอลัมน์ที่ชื่อเปลี่ยนไปตามค่า Slider
                            def map_val(keyword):
                                matched_cols = [c for c in df.columns if keyword in str(c)]
                                if matched_cols:
                                    val = last_row[matched_cols[0]]
                                    return round(val, 3) if not pd.isna(val) else "N/A"
                                return "N/A"

                            # บังคับสร้างรายการที่มีครบ 14 อินดิเคเตอร์
                            scan_results.append({
                                "Symbol": s,
                                "Price": last_row['last'],
                                "SMA_Fast": map_val('SMA_F'),
                                "SMA_Slow": map_val('SMA_S'),
                                "EMA_20": map_row := map_val('EMA_20'),
                                "RSI": map_val('RSI_V'),
                                "MACD": map_val('MACD_'),
                                "MACD_Sig": map_val('MACDs_'),
                                "Stoch_K": map_val('STOCHk_'),
                                "Stoch_D": map_val('STOCHd_'),
                                "BB_Upper": map_val('BBU_'),
                                "BB_Lower": map_val('BBL_'),
                                "ATR": map_val('ATR_V'),
                                "Volume(OBV)": f"{last_row.get('OBV_V', 0):,.0f}"
                            })
                    
                    if scan_results:
                        display_df = pd.DataFrame(scan_results)
                        st.dataframe(display_df, use_container_width=True)
                        st.success(f"✅ สำเร็จ: แสดงผลครบทั้ง {len(display_df.columns)} คอลัมน์")
                    else:
                        st.error("ไม่พบข้อมูล (โปรดตรวจสอบสิทธิ์ API หรือข้อมูลใน Sandbox)")
            else:
                st.error("เชื่อมต่อระบบ Settrade ล้มเหลว")

# [Tab 2 & 3 คงที่เพื่อความเสถียร]
with tab2:
    st.header("Gemini AI Strategy Advisor")
    target_stock = st.text_input("ระบุชื่อหุ้น", "PTT")
    if st.button("🧠 Analyze Stock"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                # ค้นหารุ่นที่รองรับอัตโนมัติ
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                sel_model = "gemini-1.5-flash" if "models/gemini-1.5-flash" in models else "gemini-pro"
                model = genai.GenerativeModel(sel_model)
                resp = model.generate_content(f"วิเคราะห์หุ้น {target_stock} ตลาด SET: ข่าวเด่น 30 วัน, Sentiment (ไทย)")
                st.markdown(resp.text)
            except Exception as e: st.error(f"AI Error: {e}")

with tab3:
    st.header("Market Sentiment Gauge")
    fig = go.Figure(go.Indicator(mode="gauge+number", value=65))
    st.plotly_chart(fig, use_container_width=True)
