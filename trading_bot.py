# --- ส่วนที่แก้ Bug (วางทับใน Loop ของหุ้นแต่ละตัว) ---
for s in stocks:
    df = engine.get_data(s)
    if df is not None:
        last = df.iloc[-1]
        
        # 💡 SOLUTION: ใช้ระบบค้นหา Column Name ด้วย Keyword (Wildcard)
        def find_indicator(keyword):
            # ค้นหาชื่อคอลัมน์ใน DataFrame ที่มีคำว่า keyword อยู่ข้างใน
            matched_cols = [c for c in df.columns if keyword in str(c)]
            if matched_cols:
                val = last[matched_cols[0]] # ดึงค่าจากคอลัมน์แรกที่เจอ
                return round(val, 3) if not pd.isna(val) else "N/A"
            return "N/A" # ถ้าไม่เจอเลย ให้แสดง N/A แทนการดีดทิ้ง

        # 📋 บังคับแสดงผลครบ 14 ค่า (Force Mapping)
        results.append({
            "Stock": s,
            "Price": last['last'],
            "SMA_F": find_indicator("SMA_F"),   # ค้นหาคำว่า SMA_F (คงที่)
            "SMA_S": find_indicator("SMA_S"),   # ค้นหาคำว่า SMA_S (คงที่)
            "RSI": find_indicator("RSI"),       # ค้นหาคำว่า RSI
            "MACD": find_indicator("MACD_"),    # ค้นหาคอลัมน์ที่มี MACD_
            "MACD_Sig": find_indicator("MACDs_"),
            "EMA_20": find_indicator("EMA_20"),
            "Stoch_K": find_indicator("STOCHk_"),
            "Stoch_D": find_indicator("STOCHd_"),
            "BB_Upper": find_indicator("BBU_"),
            "BB_Lower": find_indicator("BBL_"),
            "ATR": find_indicator("ATR_"),
            "OBV": f"{last.get('OBV_V', 0):,.0f}"
        })
