import streamlit as st
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
from settrade_v2 import Investor

# --- 1. SET PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="SRAN AI Stock Trading")

# --- 2. SIDEBAR: API & TUNING ---
with st.sidebar:
    st.header("🔑 Connectivity & Settings")
    input_app_id = st.text_input("App ID")
    input_app_secret = st.text_input("App Secret", type="password")
    gemini_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.header("⚙️ Indicator Tuning")
    sma_fast = st.slider("SMA Fast", 5, 50, 20)
    sma_slow = st.slider("SMA Slow", 20, 200, 50)
    rsi_period = st.slider("RSI Period", 5, 30, 14)

# --- 3. CREATE TABS (แก้ไขจุดที่เกิด NameError) ---
tab1, tab2 = st.tabs(["🔍 Market Scanner", "🧠 30-Day Deep Insight AI"])

# --- 4. FUNCTIONS ---
def init_market_data():
    try:
        # ใช้ App Code 'SANDBOX' เพื่อความปลอดภัยในการทดสอบ
        investor = Investor(
            app_id=input_app_id,
            app_secret=input_app_secret,
            app_code="SANDBOX", 
            broker_id="SANDBOX"
        )
        return investor.MarketData()
    except Exception as e:
        st.sidebar.error(f"Connection Error: {e}")
        return None

# --- 5. TAB 1: MARKET SCANNER ---
with tab1:
    st.header("Advanced Technical Scan")
    if st.button("🚀 Start Scanning SET"):
        market = init_market_data()
        if market:
            with st.spinner("กำลังวิเคราะห์หุ้นสำคัญในตลาด..."):
                target_stocks = ["PTT", "CPALL", "AOT", "ADVANC", "KBANK", "SCB", "OR", "GULF", "DELTA", "BANPU"]
                scan_results = []

                for symbol in target_stocks:
                    try:
                        res = market.get_candlestick(symbol, "1D", 200)
                        df = pd.DataFrame(res)
                        
                        # คำนวณอินดิเคเตอร์
                        df['SMA_F'] = ta.sma(df['last'], length=sma_fast)
                        df['SMA_S'] = ta.sma(df['last'], length=sma_slow)
                        df['RSI'] = ta.rsi(df['last'], length=rsi_period)
                        
                        last = df.iloc[-1]
                        
                        # Logic วิเคราะห์
                        signal = "Neutral"
                        if last['SMA_F'] > last['SMA_S'] and last['RSI'] < 70:
                            signal = "Bullish (Golden Cross)"
                        elif last['RSI'] < 30:
                            signal = "Oversold (Watch for Buy)"
                        elif last['RSI'] > 70:
                            signal = "Overbought (Take Profit)"

                        scan_results.append({
                            "Symbol": symbol,
                            "Last Price": last['last'],
                            "RSI": round(last['RSI'], 2),
                            "SMA Fast": round(last['SMA_F'], 2),
                            "SMA Slow": round(last['SMA_S'], 2),
                            "Signal": signal
                        })
                    except: continue
                
                st.dataframe(pd.DataFrame(scan_results), use_container_width=True)
        else:
            st.warning("กรุณากรอก App ID และ Secret ที่ Sidebar ก่อนครับ")

# --- 6. TAB 2: AI STOCK INSIGHT (1 Month) ---
with tab2:
    st.header("🧠 30-Day Deep Insight AI (Gemini)")
    stock_target = st.text_input("ระบุชื่อหุ้นที่ต้องการวิเคราะห์เชิงลึก", "PTT")
    
    if st.button("🧠 Analyze Recent 1-Month"):
        if not gemini_key:
            st.warning("กรุณาใส่ Gemini API Key ใน Sidebar ครับ")
        else:
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                with st.spinner(f"AI กำลังรวบรวมข้อมูล {stock_target} ในรอบ 30 วัน..."):
                    prompt = f"""
                    ในฐานะนักวิเคราะห์หุ้น เจาะลึกหุ้น {stock_target} ในตลาด SET:
                    1. สรุปโมเดลธุรกิจของ {stock_target} (สั้นๆ 2 บรรทัด)
                    2. สรุปข่าวสำคัญ เหตุการณ์ หรือประกาศจาก ตลท. ในรอบ "1 เดือนที่ผ่านมา" เท่านั้น
                    3. วิเคราะห์ Sentiment ตลาดล่าสุด (มีปัจจัยอะไรที่นักลงทุนกำลังให้ความสนใจ?)
                    4. ปัจจัยบวก/ลบ ที่ต้องเฝ้าระวังในอีก 1-2 สัปดาห์ข้างหน้า
                    ตอบเป็นภาษาไทย และใช้ Bullet points
                    """
                    response = model.generate_content(prompt)
                    st.markdown("### 📋 ผลการวิเคราะห์ล่าสุด (รอบ 30 วัน)")
                    st.markdown(response.text)
            except Exception as e:
                st.error(f"Gemini AI Error: {e}")
