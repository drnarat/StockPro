import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
from settrade_v2 import Investor
import warnings

# ปิด Warning กวนใจที่ทำให้ Streamlit ค้างในบางเวอร์ชัน
warnings.filterwarnings('ignore', category=FutureWarning)

# --- 1. SET PAGE CONFIG (ต้องเป็นคำสั่งแรกของ Streamlit) ---
st.set_page_config(layout="wide", page_title="SRAN AI Stock Intelligence", initial_sidebar_state="expanded")

# --- 2. SIDEBAR CONFIG ---
with st.sidebar:
    st.header("🔑 API Connection")
    app_id = st.text_input("App ID", value="")
    app_secret = st.text_input("App Secret", value="", type="password")
    gemini_key = st.text_input("Gemini API Key", value="", type="password")
    
    st.divider()
    st.header("⚙️ Indicators Settings")
    sma_f = st.slider("SMA Fast", 5, 50, 20)
    sma_s = st.slider("SMA Slow", 50, 200, 100)
    rsi_p = st.slider("RSI Period", 5, 30, 14)

# --- 3. FUNCTIONS ---
@st.cache_resource # ใช้ cache เพื่อลดภาระการโหลดบ่อยๆ
def init_investor(a_id, a_secret):
    if not a_id or not a_secret:
        return None
    try:
        investor = Investor(app_id=a_id, app_secret=a_secret, app_code="SANDBOX", broker_id="SANDBOX")
        return investor.MarketData()
    except Exception as e:
        st.error(f"Settrade Connection Error: {e}")
        return None

# --- 4. UI TABS ---
# ประกาศตัวแปร Tab ให้ชัดเจนเพื่อป้องกัน NameError
tab1, tab2 = st.tabs(["🔍 Market Scanner", "🧠 AI Insight (1 Month)"])

with tab1:
    st.header("Advanced Stock Scanner")
    if st.button("🚀 Start Scanning"):
        market = init_investor(app_id, app_secret)
        if market:
            with st.spinner("Processing Market Indicators..."):
                # รายชื่อหุ้นเป้าหมาย
                stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                scan_results = []
                
                for s in stocks:
                    try:
                        res = market.get_candlestick(s, "1D", 200)
                        df = pd.DataFrame(res)
                        
                        # คำนวณ Indicators แบบ Safe
                        df['RSI'] = ta.rsi(df['last'], length=rsi_p)
                        df['SMA_F'] = ta.sma(df['last'], length=sma_f)
                        df['SMA_S'] = ta.sma(df['last'], length=sma_s)
                        
                        last = df.iloc[-1]
                        scan_results.append({
                            "Symbol": s, 
                            "Price": last['last'],
                            "RSI": round(last['RSI'], 2),
                            "SMA_F": round(last['SMA_F'], 1),
                            "SMA_S": round(last['SMA_S'], 1),
                            "Signal": "Bullish" if last['SMA_F'] > last['SMA_S'] else "Neutral"
                        })
                    except: continue
                
                if scan_results:
                    st.dataframe(pd.DataFrame(scan_results), use_container_width=True)
                else:
                    st.warning("ดึงข้อมูลไม่สำเร็จ โปรดตรวจสอบสิทธิ์ API")
        else:
            st.info("กรุณากรอก App ID/Secret ที่ Sidebar ก่อนครับ")

with tab2:
    st.header("Gemini 30-Day Analysis")
    target = st.text_input("ชื่อหุ้น (เช่น PTT)", "PTT")
    if st.button("Analyze Stock"):
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                with st.spinner("Gemini is thinking..."):
                    prompt = f"สรุปหุ้น {target} ในตลาด SET: 1.ธุรกิจ 2.ข่าวเด่นรอบ 30 วัน 3.ปัจจัยเสี่ยงอาทิตย์หน้า (ตอบภาษาไทย)"
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
            except Exception as e:
                st.error(f"AI Error: {e}")
        else:
            st.warning("กรุณาใส่ Gemini API Key")
