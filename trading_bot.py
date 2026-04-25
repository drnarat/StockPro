import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
from settrade_v2 import Investor

# --- CONFIG AI ---
# แนะนำให้ดร. นำ API Key ของ Gemini ไปใส่ใน Streamlit Secrets หรือ Sidebar
# genai.configure(api_key="YOUR_GEMINI_API_KEY")

st.set_page_config(layout="wide", page_title="AI Stock Scanner")

# --- SIDEBAR: API CONFIG ---
with st.sidebar:
    st.header("🔑 API Settings")
    input_app_id = st.text_input("App ID")
    input_app_secret = st.text_input("App Secret", type="password")
    gemini_key = st.text_input("Gemini API Key", type="password")
    
    st.subheader("⚙️ Indicator Tuning")
    sma_fast = st.slider("SMA Fast", 5, 50, 20)
    sma_slow = st.slider("SMA Slow", 20, 200, 50)
    rsi_period = st.slider("RSI Period", 5, 30, 14)

# --- ฟังก์ชันหลัก ---
def init_settrade():
    try:
        investor = Investor(
            app_id=input_app_id,
            app_secret=input_app_secret,
            app_code="SANDBOX", # หรือโปรดักชั่น
            broker_id="SANDBOX"
        )
        return investor.MarketData()
    except:
        return None

# --- UI TABS ---
tab1, tab2 = st.tabs(["🔍 Market Scanner", "📈 AI Stock Insight"])

# --- TAB 1: ระบบสแกนหุ้นทั้งตลาด ---
with tab1:
    st.header("Market-wide Technical Scan")
    if st.button("🚀 Start Scanning SET"):
        market = init_settrade()
        if market:
            with st.spinner("กำลังดึงข้อมูลและวิเคราะห์หุ้นทั้งตลาด..."):
                # หมายเหตุ: ในการใช้จริงดร. ต้องดึงรายชื่อหุ้นจาก market.get_symbols() 
                # ตัวอย่างนี้จำลองการสแกนหุ้นหลักๆ เพื่อประสิทธิภาพ
                target_stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR"]
                scan_results = []

                for symbol in target_stocks:
                    # ดึงข้อมูลราคาย้อนหลัง 1 ปี
                    res = market.get_candlestick(symbol, "1D", 250)
                    df = pd.DataFrame(res)
                    
                    # คำนวณ Indicators ด้วย pandas-ta
                    df['SMA_Fast'] = ta.sma(df['last'], length=sma_fast)
                    df['SMA_Slow'] = ta.sma(df['last'], length=sma_slow)
                    df['RSI'] = ta.rsi(df['last'], length=rsi_period)
                    
                    last_row = df.iloc[-1]
                    
                    # Logic วิเคราะห์เบื้องต้น
                    signal = "Wait"
                    if last_row['SMA_Fast'] > last_row['SMA_Slow'] and last_row['RSI'] < 70:
                        signal = "Strong Buy (Golden Cross)"
                    elif last_row['RSI'] < 30:
                        signal = "Oversold (Possible Buy)"
                    elif last_row['RSI'] > 70:
                        signal = "Overbought (Caution)"

                    scan_results.append({
                        "Symbol": symbol,
                        "Price": last_row['last'],
                        "RSI": round(last_row['RSI'], 2),
                        "Signal": signal
                    })
                
                st.table(pd.DataFrame(scan_results))
        else:
            st.error("กรุณาเชื่อมต่อ API ก่อนครับ")

# --- TAB 2: วิเคราะห์หุ้นรายตัวโดย Gemini ---
with tab2:
    st.header("Gemini AI Fundamental Analyst")
    target_symbol = st.text_input("ระบุชื่อหุ้นที่ต้องการวิเคราะห์ (เช่น PTT)", "PTT")
    
    if st.button("🧠 Analyze with Gemini"):
        if not gemini_key:
            st.warning("กรุณาใส่ Gemini API Key ที่ Sidebar ครับ")
        else:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-2.5-flash') # หรือเวอร์ชันล่าสุด
            
            with st.spinner(f"AI กำลังรวบรวมข้อมูล {target_symbol}..."):
                # สร้าง Prompt ให้ Gemini วิเคราะห์
                prompt = f"""
                ในฐานะนักวิเคราะห์หุ้นมืออาชีพ ช่วยสรุปข้อมูลหุ้น {target_symbol} ในตลาดหลักทรัพย์แห่งประเทศไทย:
                1. อธิบายโมเดลธุรกิจสั้นๆ ให้เข้าใจง่าย
                2. สรุปข่าวสำคัญหรือเหตุการณ์ในรอบ 1 ปีที่ผ่านมาที่มีผลต่อราคาหุ้น
                3. วิเคราะห์ปัจจัยบวกและปัจจัยลบในปัจจุบัน
                ตอบเป็นภาษาไทย และใช้รูปแบบที่อ่านง่าย (Bullet points)
                """
                
                response = model.generate_content(prompt)
                st.markdown("### 📋 บทวิเคราะห์จาก AI")
                st.write(response.text)
