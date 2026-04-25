import streamlit as st
import requests
import json

st.set_page_config(
    page_title="Stock Pro",
    page_icon="S",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
html,body,[class*="css"]{font-family:'Sarabun',sans-serif;background:#0a0f1a;color:#e2e8f0}
footer{visibility:hidden}#MainMenu{visibility:hidden}header{visibility:hidden}
.stButton>button{background:#10b981;color:#fff;border:none;border-radius:12px;
  padding:14px 20px;font-size:16px;font-weight:700;font-family:'Sarabun',sans-serif;
  width:100%;transition:opacity .15s}
.stButton>button:hover{opacity:.85;border:none}
.stTextInput>div>div>input,.stSelectbox>div>div>select{
  background:#111827;color:#e2e8f0;border:1px solid #1e2d45;border-radius:10px;
  font-family:'Sarabun',sans-serif;font-size:15px}
.stTabs [data-baseweb="tab"]{font-size:15px;font-weight:600;padding:12px 20px}
.stTabs [data-baseweb="tab-list"]{gap:0;background:#111827;border-radius:12px;padding:4px}
.stTabs [aria-selected="true"]{background:#10b981;color:#fff;border-radius:9px}
.card{background:#1a2235;border:1px solid #1e2d45;border-radius:16px;padding:18px;margin-bottom:12px}
.card-buy{border-left:4px solid #10b981}
.card-sell{border-left:4px solid #ef4444}
.card-watch{border-left:4px solid #f59e0b}
.price-big{font-size:32px;font-weight:700;font-family:'JetBrains Mono',monospace}
.sym-big{font-size:24px;font-weight:700;font-family:'JetBrains Mono',monospace}
.ind-lbl{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px}
.ind-val{font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace}
.bull{color:#10b981}.bear{color:#ef4444}.neut{color:#f59e0b}
div[data-testid="stExpander"]{background:#1a2235;border:1px solid #1e2d45;border-radius:12px}
.stProgress>div>div>div{background:#10b981}
</style>
""", unsafe_allow_html=True)

# ── CLAUDE API ────────────────────────────────────────────────
def claude_ask(prompt: str, max_tokens: int = 800) -> str:
    """Call Claude API with web search"""
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"Content-Type": "application/json"},
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "tools": [{"type": "web_search_20250305", "name": "web_search"}],
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    txt = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            txt += block["text"]
    return txt.strip()

def parse_json_robust(txt: str) -> dict | None:
    """Extract JSON from Claude response robustly"""
    import re
    if not txt:
        return None
    # Try direct parse
    try:
        return json.loads(txt.strip())
    except Exception:
        pass
    # Strip markdown fences
    cleaned = re.sub(r"```json\s*", "", txt, flags=re.IGNORECASE)
    cleaned = re.sub(r"```", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # Find first { } block
    start = txt.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(txt[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = txt[start:i+1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        # Fix common issues
                        fixed = re.sub(r",(\s*[}\]])", r"\1", candidate)
                        try:
                            return json.loads(fixed)
                        except Exception:
                            pass
                    break
    return None

def get_num(d: dict, *keys, default=0.0) -> float:
    """Safely extract number from dict with multiple key aliases"""
    for k in keys:
        for variant in [k, k.lower(), k.upper(), k.replace("_",""), k.replace(" ","_")]:
            v = d.get(variant)
            if v is not None and v != "":
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
    return default

# ── SCORING ───────────────────────────────────────────────────
def score_stock(d: dict, rsi_os=35, rsi_ob=65) -> dict:
    price   = get_num(d, "price", "close", "last", "current_price")
    chg     = get_num(d, "chg", "change", "change_pct")
    chg5    = get_num(d, "chg5", "change5", "change_5d")
    rsi     = get_num(d, "rsi", "rsi14", default=50)
    macd    = get_num(d, "macd", "macd_hist")
    bbp     = get_num(d, "bb_pct", "bbp", default=0.5)
    stoch   = get_num(d, "stoch", "stochastic", default=50)
    adx     = get_num(d, "adx", default=20)
    dip     = get_num(d, "di_plus", "diplus", default=25)
    dim     = get_num(d, "di_minus", "diminus", default=25)
    vwap    = get_num(d, "vwap", default=price)
    vol_r   = get_num(d, "vol_ratio", "volume_ratio", default=1)
    sma20   = get_num(d, "sma20", "sma_20", default=price)
    sma50   = get_num(d, "sma50", "sma_50", default=price)
    sma200  = get_num(d, "sma200", "sma_200", default=price)
    atr     = get_num(d, "atr", default=price * 0.02)
    h52     = get_num(d, "h52", "high52", "52w_high", default=price)
    l52     = get_num(d, "l52", "low52", "52w_low", default=price)
    name    = d.get("name", d.get("company", ""))
    pe      = get_num(d, "pe", "pe_ratio", default=0)

    sc = 50
    bs, ss, ns = [], [], []

    if rsi < rsi_os:   sc += 8;  bs.append(f"RSI {rsi:.1f} Oversold")
    elif rsi > rsi_ob: sc -= 8;  ss.append(f"RSI {rsi:.1f} Overbought")
    else:              ns.append(f"RSI {rsi:.1f} ปกติ")

    if macd > 0:   sc += 7; bs.append("MACD บวก momentum ขาขึ้น")
    elif macd < 0: sc -= 7; ss.append("MACD ลบ momentum ขาลง")

    if price > sma20 > sma50:   sc += 6; bs.append("ราคา > SMA20 > SMA50 uptrend")
    elif price < sma20 < sma50: sc -= 6; ss.append("ราคา < SMA20 < SMA50 downtrend")
    if sma200 > 0:
        if price > sma200: sc += 4; bs.append("เหนือ SMA200")
        else:              sc -= 4; ss.append("ต่ำกว่า SMA200")

    if bbp < 0.2:  sc += 6; bs.append("BB% ใกล้ Lower oversold")
    elif bbp > 0.8: sc -= 5; ss.append("BB% ใกล้ Upper overbought")

    if stoch < 20:  sc += 5; bs.append("Stochastic oversold")
    elif stoch > 80: sc -= 5; ss.append("Stochastic overbought")

    if adx > 20:
        if dip > dim:   sc += 5; bs.append(f"ADX {adx:.0f} uptrend แข็ง")
        elif dim > dip: sc -= 5; ss.append(f"ADX {adx:.0f} downtrend")
    else: ns.append(f"ADX {adx:.0f} sideways")

    if price > 0 and vwap > 0:
        if price > vwap: sc += 3; bs.append("ราคา > VWAP")
        else:            sc -= 3; ss.append("ราคา < VWAP")

    if vol_r > 1.5:  sc += 3; bs.append(f"Volume {vol_r:.1f}x ค่าเฉลี่ย")
    elif vol_r < 0.5: ns.append("Volume ต่ำ ระวังสัญญาณหลอก")

    sc = max(0, min(100, sc))
    sig = "buy" if sc >= 65 else "sell" if sc <= 35 else "watch" if sc >= 55 else "hold"
    at = atr or price * 0.02
    entry = round(price * 0.985, 2)
    t1    = round(price + at * 2, 2)
    t2    = round(price + at * 3.5, 2)
    sl    = round(price - at * 1.5, 2)
    up    = round(((t1 / price) - 1) * 100, 1) if price > 0 else 0
    dn    = round(((price / sl) - 1) * 100, 1) if sl > 0 else 1
    rr    = round(up / dn, 2) if dn > 0 else 0

    return dict(
        sc=sc, sig=sig, bs=bs, ss=ss, ns=ns,
        price=price, chg=chg, chg5=chg5, rsi=rsi, macd=macd,
        bbp=bbp, stoch=stoch, adx=adx, dip=dip, dim=dim,
        vwap=vwap, vol_r=vol_r, sma20=sma20, sma50=sma50,
        sma200=sma200, atr=atr, h52=h52, l52=l52,
        entry=entry, t1=t1, t2=t2, sl=sl, up=up, dn=dn, rr=rr,
        name=name, pe=pe
    )

# ── STOCK LIST ────────────────────────────────────────────────
SET50 = [
    ("KBANK","กสิกรไทย"),("BBL","กรุงเทพ"),("SCB","ไทยพาณิชย์"),
    ("KTB","กรุงไทย"),("BAY","กรุงศรี"),("TTB","ทหารไทยธนชาต"),
    ("TISCO","ทิสโก้"),("KKP","เกียรตินาคินภัทร"),
    ("PTT","ปตท."),("PTTEP","ปตท.สผ."),("PTTGC","พีทีที โกลบอล"),
    ("GULF","กัลฟ์"),("GPSC","โกลบอล เพาเวอร์"),
    ("RATCH","ราช กรุ๊ป"),("BGRIM","บี.กริม"),("EGCO","เอ็กโก"),("CKP","ซีเค เพาเวอร์"),
    ("ADVANC","แอดวานซ์"),("TRUE","ทรู"),("INTUCH","อินทัช"),
    ("CPALL","ซีพี ออลล์"),("CRC","เซ็นทรัล รีเทล"),
    ("HMPRO","โฮม โปรดักส์"),("MAKRO","สยามแม็คโคร"),("BJC","เบอร์ลี่ ยุคเกอร์"),
    ("CPF","ซีพีเอฟ"),("TU","ไทยยูเนี่ยน"),("GFPT","จีเอฟพีที"),
    ("CBG","คาราบาวกรุ๊ป"),("OSP","โอสถสภา"),
    ("LH","แลนด์แอนด์เฮ้าส์"),("AP","เอพี"),("SIRI","แสนสิริ"),("QH","ควอลิตี้เฮ้าส์"),
    ("AOT","ท่าอากาศยานไทย"),("MINT","ไมเนอร์"),("ERW","อีอาร์ดับบลิว"),
    ("BDMS","กรุงเทพดุสิตเวชการ"),("BGH","กรุงเทพ เชน"),("BCH","บางกอก เชน"),
    ("SCC","ปูนซิเมนต์ไทย"),("SCCC","ปูนซีเมนต์นครหลวง"),("IVL","อินโดรามา"),
    ("MTC","เมืองไทย แคปปิตอล"),("TIDLOR","ทีดีแอล"),
    ("SAWAD","ซาวัด"),("AEONTS","อิออน"),("MBK","เอ็มบีเค"),
    ("DELTA","เดลต้า"),("WHA","ดับบลิวเอชเอ"),
]
US_TECH = [
    ("AAPL","Apple"),("MSFT","Microsoft"),("NVDA","NVIDIA"),("GOOGL","Alphabet"),
    ("META","Meta"),("AMZN","Amazon"),("TSLA","Tesla"),("AMD","AMD"),
    ("INTC","Intel"),("AVGO","Broadcom"),("QCOM","Qualcomm"),("MU","Micron"),
    ("CRM","Salesforce"),("ADBE","Adobe"),("NOW","ServiceNow"),
    ("PLTR","Palantir"),("ORCL","Oracle"),("AMAT","Applied Materials"),
]
CN_TECH = [
    ("BABA","Alibaba"),("JD","JD.com"),("BIDU","Baidu"),("NTES","NetEase"),
    ("PDD","Pinduoduo"),("TCOM","Trip.com"),("NIO","NIO"),("XPEV","XPeng"),
    ("LI","Li Auto"),("BILI","Bilibili"),("WB","Weibo"),("FUTU","Futu"),
]
MARKETS = {"SET50 (50 ตัว)": SET50, "US Tech (18 ตัว)": US_TECH, "CN Tech (12 ตัว)": CN_TECH}
MKT_CUR = {"SET50 (50 ตัว)": "฿", "US Tech (18 ตัว)": "$", "CN Tech (12 ตัว)": "$"}
MKT_DESC = {
    "SET50 (50 ตัว)": "Thai SET market, price in Thai Baht (THB)",
    "US Tech (18 ตัว)": "NASDAQ/NYSE US market, price in USD",
    "CN Tech (12 ตัว)": "NYSE/NASDAQ CN ADR, price in USD"
}

def fmt(v, d=2):
    if v is None or v == 0: return "--"
    return f"{v:,.{d}f}"

def pct(v, d=2):
    if v is None: return "--"
    s = "+" if v >= 0 else ""
    return f"{s}{v:.{d}f}%"

def sig_color(sig):
    return {"buy":"🟢","sell":"🔴","watch":"🟡","hold":"⚪"}.get(sig,"⚪")

def sig_th(sig):
    return {"buy":"ซื้อ","sell":"ขาย","watch":"เฝ้าระวัง","hold":"ถือ"}.get(sig,"ถือ")

# ── HEADER ────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:20px 0 10px">
  <div style="font-size:28px;font-weight:700;color:#e2e8f0">Stock Pro</div>
  <div style="font-size:14px;color:#64748b;margin-top:4px">AI วิเคราะห์หุ้น · SET50 · US · CN</div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🔍 สแกนหุ้น", "📊 วิเคราะห์", "📡 Real-time"])

# ════════════════════════════════════════
# TAB 1: SCANNER
# ════════════════════════════════════════
with tab1:
    st.markdown("### สแกนหาหุ้นน่าสนใจ")

    col1, col2 = st.columns(2)
    with col1:
        mkt_sel = st.selectbox("ตลาด", list(MARKETS.keys()), key="sc_mkt")
    with col2:
        sig_sel = st.selectbox("สัญญาณ", ["ทั้งหมด","ซื้อ","ซื้อ+เฝ้าระวัง","ขาย"], key="sc_sig")

    with st.expander("⚙️ Parameters"):
        c1, c2 = st.columns(2)
        with c1:
            min_sc = st.slider("คะแนนขั้นต่ำ", 0, 100, 50)
            rsi_os = st.slider("RSI Oversold", 20, 45, 35)
        with c2:
            min_rr = st.slider("R/R ขั้นต่ำ", 0.5, 3.0, 1.0, step=0.1)
            rsi_ob = st.slider("RSI Overbought", 55, 80, 65)

    if st.button("🔍 เริ่มสแกน", key="scan_btn"):
        stocks = MARKETS[mkt_sel]
        cur    = MKT_CUR[mkt_sel]
        mktd   = MKT_DESC[mkt_sel]
        allowed = {
            "ทั้งหมด": ["buy","sell","watch","hold"],
            "ซื้อ": ["buy"],
            "ซื้อ+เฝ้าระวัง": ["buy","watch"],
            "ขาย": ["sell"]
        }[sig_sel]

        results = []
        prog = st.progress(0, text="กำลังสแกน...")
        status = st.empty()

        for i, (sym, name) in enumerate(stocks):
            status.text(f"ดึงข้อมูล {sym} ({i+1}/{len(stocks)})")
            prompt = (
                f"Search Yahoo Finance for current technical data of {sym} stock on {mktd}.\n"
                "Return ONLY valid JSON (no markdown, no explanation). Start response with {:\n"
                '{"price":0,"chg":0,"rsi":50,"macd":0,"bb_pct":0.5,"stoch":50,'
                '"adx":20,"di_plus":25,"di_minus":25,"vwap":0,"vol_ratio":1,'
                '"sma20":0,"sma50":0,"sma200":0,"atr":0,"h52":0,"l52":0}'
            )
            try:
                txt = claude_ask(prompt, 500)
                d = parse_json_robust(txt)
                if d and get_num(d, "price", "close", "last") > 0:
                    d["name"] = name
                    S = score_stock(d, rsi_os, rsi_ob)
                    if S["sc"] >= min_sc and S["rr"] >= min_rr and S["sig"] in allowed:
                        results.append((sym, name, cur, S))
            except Exception as e:
                st.warning(f"Skip {sym}: {e}")
            prog.progress((i+1)/len(stocks), text=f"สแกน {sym}...")

        prog.empty(); status.empty()

        results.sort(key=lambda x: -x[3]["sc"])
        st.success(f"พบ **{len(results)}** หุ้น จาก {len(stocks)} ตัว")

        for sym, name, cur, S in results:
            up_c  = "#10b981" if S["chg"] >= 0 else "#ef4444"
            lc    = {"buy":"card-buy","sell":"card-sell","watch":"card-watch"}.get(S["sig"],"card")
            st.markdown(f"""
            <div class="card {lc}">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
                <div>
                  <div class="sym-big" style="font-size:20px">{sym}</div>
                  <div style="font-size:13px;color:#64748b">{name}</div>
                  <div style="margin-top:8px">{sig_color(S['sig'])} <b style="color:#e2e8f0">{sig_th(S['sig'])}</b>
                    &nbsp;<span style="font-size:12px;color:#64748b">R/R {S['rr']}</span></div>
                </div>
                <div style="text-align:right">
                  <div style="font-size:22px;font-weight:700;font-family:'JetBrains Mono',monospace;color:{up_c}">{cur}{fmt(S['price'])}</div>
                  <div style="font-size:14px;color:{up_c};font-weight:700">{pct(S['chg'])}</div>
                  <div style="font-size:20px;font-weight:700;color:{'#10b981' if S['sc']>=65 else '#f59e0b' if S['sc']>=45 else '#ef4444'}">{S['sc']}</div>
                </div>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-bottom:10px">
                {"".join(f'<div class="ibox"><div class="ind-lbl">{l}</div><div class="ind-val {"bull" if b else "bear" if r else ""}">{v}</div></div>'
                  for l,v,b,r in [
                    ("RSI", f"{S['rsi']:.1f}", S['rsi']<rsi_os, S['rsi']>rsi_ob),
                    ("ADX", f"{S['adx']:.1f}", S['adx']>20 and S['dip']>S['dim'], S['adx']>20 and S['dim']>S['dip']),
                    ("BB%", f"{S['bbp']:.2f}", S['bbp']<0.2, S['bbp']>0.8),
                    ("Vol", f"{S['vol_r']:.1f}x", S['vol_r']>1.5, False)
                  ])}
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px">
                <div style="text-align:center;background:#111827;border-radius:8px;padding:8px">
                  <div style="font-size:11px;color:#64748b">จุดซื้อ</div>
                  <div style="font-size:13px;font-weight:700;color:#3b82f6;font-family:'JetBrains Mono',monospace">{cur}{fmt(S['entry'])}</div>
                </div>
                <div style="text-align:center;background:#111827;border-radius:8px;padding:8px">
                  <div style="font-size:11px;color:#64748b">เป้า 1</div>
                  <div style="font-size:13px;font-weight:700;color:#10b981;font-family:'JetBrains Mono',monospace">{cur}{fmt(S['t1'])}</div>
                </div>
                <div style="text-align:center;background:#111827;border-radius:8px;padding:8px">
                  <div style="font-size:11px;color:#64748b">เป้า 2</div>
                  <div style="font-size:13px;font-weight:700;color:#34d399;font-family:'JetBrains Mono',monospace">{cur}{fmt(S['t2'])}</div>
                </div>
                <div style="text-align:center;background:#111827;border-radius:8px;padding:8px">
                  <div style="font-size:11px;color:#64748b">Stop</div>
                  <div style="font-size:13px;font-weight:700;color:#ef4444;font-family:'JetBrains Mono',monospace">{cur}{fmt(S['sl'])}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"วิเคราะห์ {sym} เจาะลึก →", key=f"da_{sym}"):
                st.session_state["da_sym"] = sym
                st.session_state["da_mkt"] = "SET" if "SET" in mkt_sel else ("US" if "US" in mkt_sel else "CN")
                st.rerun()

# ════════════════════════════════════════
# TAB 2: DEEP ANALYSIS
# ════════════════════════════════════════
with tab2:
    st.markdown("### วิเคราะห์หุ้นเจาะลึก")

    col1, col2 = st.columns([3,1])
    with col1:
        sym_in = st.text_input("ชื่อหุ้น (Ticker)", 
                               value=st.session_state.get("da_sym",""),
                               placeholder="เช่น ADVANC, PTT, NVDA, BABA")
    with col2:
        mkt_in = st.selectbox("ตลาด", ["SET","US","CN"],
                              index=["SET","US","CN"].index(st.session_state.get("da_mkt","SET")))

    if st.button("📊 วิเคราะห์เจาะลึก", key="da_btn"):
        sym = sym_in.strip().upper()
        if not sym:
            st.warning("กรุณาใส่ชื่อหุ้น")
        else:
            cur   = "฿" if mkt_in == "SET" else "$"
            mktd  = MKT_DESC.get(
                next((k for k in MARKETS if mkt_in in k), "US Tech (18 ตัว)"),
                f"{mkt_in} market"
            )

            with st.spinner(f"กำลังดึงข้อมูล {sym}..."):
                prompt = (
                    f"Search Yahoo Finance for current technical analysis data of {sym} on {mktd}.\n"
                    "Return ONLY valid JSON starting with {, no other text:\n"
                    '{"name":"Company Name","price":0,"chg":0,"chg5":0,"rsi":50,"macd":0,'
                    '"bb_pct":0.5,"stoch":50,"adx":20,"di_plus":25,"di_minus":25,'
                    '"vwap":0,"vol_ratio":1,"sma20":0,"sma50":0,"sma200":0,'
                    '"atr":0,"h52":0,"l52":0,"pe":0}'
                )
                try:
                    txt = claude_ask(prompt, 600)
                    d   = parse_json_robust(txt)
                    if not d:
                        st.error(f"ดึงข้อมูลไม่ได้ Claude ตอบว่า:\n{txt[:300]}")
                        st.stop()
                    price = get_num(d,"price","close","last")
                    if price <= 0:
                        st.error(f"ไม่พบราคา {sym} — ตรวจชื่อหุ้น")
                        st.stop()
                    S = score_stock(d)
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.stop()

            # Display result
            up_c = "#10b981" if S["chg"] >= 0 else "#ef4444"
            p52  = max(0, min(100, (S["price"]-S["l52"])/(S["h52"]-S["l52"]+1e-9)*100)) if S["h52"] > S["l52"] else 50

            st.markdown(f"""
            <div class="card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px">
                <div>
                  <div class="sym-big">{sym}</div>
                  <div style="font-size:13px;color:#64748b;margin-top:3px">{S['name']} · {mkt_in}</div>
                  <div style="margin-top:10px">{sig_color(S['sig'])} <b style="font-size:16px;color:#e2e8f0">{sig_th(S['sig'])}</b></div>
                </div>
                <div style="text-align:right">
                  <div style="font-size:28px;font-weight:700;color:{'#10b981' if S['sc']>=65 else '#f59e0b' if S['sc']>=45 else '#ef4444'}">{S['sc']}</div>
                  <div style="font-size:11px;color:#64748b">/100 คะแนน</div>
                </div>
              </div>
              <div class="price-big" style="color:{up_c}">{cur}{fmt(S['price'])}</div>
              <div style="font-size:15px;color:{up_c};font-weight:700;margin-top:5px">{pct(S['chg'])} วันนี้ &nbsp;
                <span style="color:#64748b;font-weight:400">{pct(S['chg5'],1)} 5 วัน</span></div>
              {f'<div style="font-size:13px;color:#64748b;margin-top:5px">P/E: {fmt(S["pe"],1)}</div>' if S["pe"] else ""}
            </div>
            """, unsafe_allow_html=True)

            # Indicators
            col_a, col_b = st.columns(2)
            for col, items in [
                (col_a, [
                    ("RSI (14)", f"{S['rsi']:.1f}", S['rsi']<35, S['rsi']>65),
                    ("MACD Hist", f"{S['macd']:.4f}", S['macd']>0, S['macd']<0),
                    ("Bollinger %B", f"{S['bbp']:.2f}", S['bbp']<0.2, S['bbp']>0.8),
                    ("Stochastic %K", f"{S['stoch']:.1f}", S['stoch']<20, S['stoch']>80),
                ]),
                (col_b, [
                    ("ADX", f"{S['adx']:.1f}", S['adx']>20 and S['dip']>S['dim'], S['adx']>20 and S['dim']>S['dip']),
                    ("Vol Ratio", f"{S['vol_r']:.2f}x", S['vol_r']>1.5, S['vol_r']<0.5),
                    ("vs SMA50", pct((S['price']/S['sma50']-1)*100 if S['sma50'] else 0,1), S['price']>S['sma50'], S['price']<S['sma50']),
                    ("VWAP", f"{cur}{fmt(S['vwap'])}", S['price']>S['vwap'], S['price']<S['vwap']),
                ]),
            ]:
                with col:
                    for lbl, val, bull, bear in items:
                        cls = "bull" if bull else "bear" if bear else "neut"
                        badge = "▲ Bullish" if bull else "▼ Bearish" if bear else "→ Neutral"
                        st.markdown(f"""
                        <div style="background:#111827;border-radius:10px;padding:10px;margin-bottom:8px">
                          <div style="font-size:11px;color:#64748b;text-transform:uppercase">{lbl}</div>
                          <div style="font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace" class="{cls}">{val}</div>
                          <div style="font-size:11px" class="{cls}">{badge}</div>
                        </div>
                        """, unsafe_allow_html=True)

            # Targets
            st.markdown("#### 🎯 ราคาเป้าหมาย")
            tc1, tc2, tc3, tc4 = st.columns(4)
            for col, lbl, val, color in [
                (tc1, "จุดซื้อ", f"{cur}{fmt(S['entry'])}", "#3b82f6"),
                (tc2, "เป้า 1",  f"{cur}{fmt(S['t1'])}",   "#10b981"),
                (tc3, "เป้า 2",  f"{cur}{fmt(S['t2'])}",   "#34d399"),
                (tc4, "Stop Loss",f"{cur}{fmt(S['sl'])}",  "#ef4444"),
            ]:
                with col:
                    st.markdown(f"""
                    <div style="background:#111827;border-radius:10px;padding:10px;text-align:center">
                      <div style="font-size:11px;color:#64748b">{lbl}</div>
                      <div style="font-size:14px;font-weight:700;color:{color};font-family:'JetBrains Mono',monospace;margin-top:4px">{val}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown(f"**Risk/Reward:** 1 : {S['rr']}  &nbsp;|&nbsp;  +{S['up']}% / -{S['dn']}%")

            # 52W
            if S["h52"] > S["l52"]:
                st.markdown(f"**52-Week Range:** {cur}{fmt(S['l52'])} — {cur}{fmt(S['h52'])}")
                st.progress(p52/100)

            # Signals
            if S["bs"]:
                st.markdown("**🟢 สัญญาณซื้อ**")
                for s in S["bs"]: st.markdown(f"- {s}")
            if S["ss"]:
                st.markdown("**🔴 สัญญาณขาย**")
                for s in S["ss"]: st.markdown(f"- {s}")

            # AI News Analysis
            st.markdown("---")
            st.markdown("#### 📰 AI วิเคราะห์ + ข่าวสำคัญ 1 ปี")
            with st.spinner("AI กำลังค้นข่าว..."):
                try:
                    mktd2 = "ตลาดหุ้นไทย" if mkt_in=="SET" else f"ตลาด {mkt_in}"
                    news_prompt = (
                        f"วิเคราะห์หุ้น {sym} ({mktd2}) ดังนี้:\n"
                        f"1. ค้นข่าวสำคัญ 1 ปีที่ผ่านมาที่กระทบราคา ระบุ บวก/ลบ/กลาง\n"
                        f"2. ปัจจัยพื้นฐาน แนวโน้มธุรกิจ\n"
                        f"3. สรุปเทคนิค: ราคา={cur}{fmt(S['price'])}, RSI={S['rsi']:.1f}, Score={S['sc']}/100\n"
                        f"4. คำแนะนำ: ซื้อที่ {cur}{S['entry']} เป้า1={cur}{S['t1']} เป้า2={cur}{S['t2']} SL={cur}{S['sl']} R/R={S['rr']}\n"
                        f"5. ความเสี่ยง\nตอบภาษาไทย กระชับ"
                    )
                    news_txt = claude_ask(news_prompt, 1800)
                    st.markdown(news_txt)
                except Exception as e:
                    st.error(f"ข่าว error: {e}")

# ════════════════════════════════════════
# TAB 3: REAL-TIME
# ════════════════════════════════════════
with tab3:
    st.markdown("### Real-time ราคาหุ้น")
    st.info("กดปุ่ม **Refresh** เพื่ออัปเดตราคาล่าสุด (AI ดึงข้อมูลใหม่)")

    if "rt_list" not in st.session_state:
        st.session_state.rt_list = [
            ("ADVANC","SET"),("PTT","SET"),("NVDA","US")
        ]

    # Add stock
    ca, cb, cc = st.columns([2,1,1])
    with ca: new_sym = st.text_input("Ticker", placeholder="เช่น KBANK, AAPL", label_visibility="collapsed")
    with cb: new_mkt = st.selectbox("ตลาด", ["SET","US","CN"], label_visibility="collapsed", key="rt_mkt_sel")
    with cc:
        if st.button("+ เพิ่ม"):
            sym2 = new_sym.strip().upper()
            if sym2 and (sym2, new_mkt) not in st.session_state.rt_list:
                st.session_state.rt_list.append((sym2, new_mkt))
                st.rerun()

    if st.button("🔄 Refresh ราคาทั้งหมด"):
        for i, (sym2, mkt2) in enumerate(st.session_state.rt_list):
            cur2   = "฿" if mkt2=="SET" else "$"
            mktd2  = "Thai SET (THB)" if mkt2=="SET" else f"{mkt2} (USD)"
            prompt2 = (
                f"Search current price of {sym2} stock on {mktd2}. "
                "Return ONLY JSON starting with {:\n"
                '{"price":0,"chg":0,"rsi":50,"ema12":0,"ema26":0,"sma20":0}'
            )
            try:
                with st.spinner(f"ดึง {sym2}..."):
                    txt2 = claude_ask(prompt2, 250)
                    d2   = parse_json_robust(txt2)
                if d2:
                    price2 = get_num(d2,"price","close","last")
                    chg2   = get_num(d2,"chg","change")
                    rsi2   = get_num(d2,"rsi",default=50)
                    e12    = get_num(d2,"ema12",default=price2)
                    e26    = get_num(d2,"ema26",default=price2)
                    s20    = get_num(d2,"sma20",default=price2)
                    sc2 = 50
                    if rsi2 < 35: sc2 += 10
                    elif rsi2 > 65: sc2 -= 10
                    if e12 > e26: sc2 += 8
                    else: sc2 -= 8
                    if price2 > s20: sc2 += 6
                    else: sc2 -= 6
                    sc2 = max(0, min(100, sc2))
                    sig2 = "buy" if sc2>=65 else "sell" if sc2<=35 else "watch" if sc2>=55 else "hold"
                    up2c = "#10b981" if chg2>=0 else "#ef4444"

                    st.markdown(f"""
                    <div class="card {'card-'+sig2 if sig2 in ['buy','sell','watch'] else 'card'}">
                      <div style="display:flex;justify-content:space-between;align-items:center">
                        <div>
                          <span style="font-size:18px;font-weight:700;font-family:'JetBrains Mono',monospace">{sym2}</span>
                          <span style="font-size:13px;color:#64748b;margin-left:8px">{mkt2}</span>
                          <div style="margin-top:6px">{sig_color(sig2)} {sig_th(sig2)} &nbsp;
                            <span style="font-size:13px;color:#64748b">Score {sc2}</span></div>
                        </div>
                        <div style="text-align:right">
                          <div style="font-size:22px;font-weight:700;color:{up2c};font-family:'JetBrains Mono',monospace">{cur2}{fmt(price2)}</div>
                          <div style="font-size:14px;color:{up2c};font-weight:700">{pct(chg2)}</div>
                        </div>
                      </div>
                      <div style="background:#1e2d45;border-radius:4px;height:5px;margin-top:10px">
                        <div style="width:{sc2}%;height:5px;border-radius:4px;background:{'#10b981' if sc2>=65 else '#ef4444' if sc2<=35 else '#f59e0b'}"></div>
                      </div>
                      <div style="font-size:12px;color:#64748b;margin-top:4px">RSI {rsi2:.0f} · {"EMA bullish" if e12>e26 else "EMA bearish"} · {"เหนือ SMA20" if price2>s20 else "ต่ำกว่า SMA20"}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning(f"ดึง {sym2} ไม่ได้")
            except Exception as e:
                st.error(f"{sym2}: {e}")

    # Remove stock
    st.markdown("---")
    st.markdown("**จัดการ Watchlist**")
    for sym3, mkt3 in list(st.session_state.rt_list):
        c1, c2 = st.columns([4,1])
        with c1: st.write(f"**{sym3}** ({mkt3})")
        with c2:
            if st.button("ลบ", key=f"rm_{sym3}_{mkt3}"):
                st.session_state.rt_list.remove((sym3,mkt3))
                st.rerun()

st.markdown('<div style="text-align:center;font-size:11px;color:#334155;margin-top:20px">ใช้เพื่อการศึกษา ไม่ใช่คำแนะนำการลงทุน</div>', unsafe_allow_html=True)
