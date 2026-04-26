# Stock Pro — Streamlit App
# Settrade API (SET real-time) + yfinance (US/CN) + Claude AI
#
# ตั้งค่า Secrets ใน Streamlit Cloud:
#   [settrade]
#   app_id     = "YOUR_APP_ID"
#   app_secret = "YOUR_APP_SECRET"
#   app_code   = "YOUR_APP_CODE"
#   broker_id  = "YOUR_BROKER_ID"

import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import time
from datetime import datetime

# ── Library checks ───────────────────────────────────────────
try:
    from settrade_v2 import Investor
    SETTRADE_OK = True
except ImportError:
    SETTRADE_OK = False

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Pro",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Sarabun',sans-serif;background:#07101f;color:#dce8f5}
footer,#MainMenu,header{visibility:hidden}
.stButton>button{background:linear-gradient(135deg,#059669,#047857);color:#fff;border:none;
  border-radius:10px;padding:12px 20px;font-size:15px;font-weight:700;
  font-family:'Sarabun',sans-serif;width:100%;transition:all .2s}
.stButton>button:hover{opacity:.88;transform:translateY(-1px)}
.stButton>button:disabled{opacity:.4}
.stTextInput>div>div>input,.stSelectbox>div>div>select,.stNumberInput>div>div>input{
  background:#0d1829;color:#dce8f5;border:1px solid #1c2e4a;border-radius:8px;
  font-family:'Sarabun',sans-serif;font-size:15px}
.stTabs [data-baseweb="tab-list"]{background:#0d1829;border-radius:10px;padding:4px;gap:2px}
.stTabs [data-baseweb="tab"]{font-size:14px;font-weight:600;padding:10px 16px;
  color:#5d7a9a;font-family:'Sarabun',sans-serif}
.stTabs [aria-selected="true"]{background:#059669;color:#fff;border-radius:8px}
div[data-testid="stExpander"]{background:#0d1829;border:1px solid #1c2e4a;border-radius:10px}
div[data-testid="stMetric"]{background:#0d1829;border:1px solid #1c2e4a;border-radius:10px;padding:14px}

.sc{background:#0d1829;border:1px solid #1c2e4a;border-radius:14px;padding:16px;margin-bottom:12px}
.sc.buy  {border-left:4px solid #059669}
.sc.sell {border-left:4px solid #dc2626}
.sc.watch{border-left:4px solid #d97706}
.mono{font-family:'IBM Plex Mono',monospace}
.bull{color:#059669}.bear{color:#dc2626}.neut{color:#d97706}.dim{color:#5d7a9a}
.px-xl{font-size:30px;font-weight:700;font-family:'IBM Plex Mono',monospace}
.px-lg{font-size:22px;font-weight:700;font-family:'IBM Plex Mono',monospace}
.sym-lg{font-size:20px;font-weight:700;font-family:'IBM Plex Mono',monospace}
.ib{background:#07101f;border:1px solid #1c2e4a;border-radius:8px;padding:10px;text-align:center;margin-bottom:7px}
.ib .lbl{font-size:11px;color:#5d7a9a;text-transform:uppercase;letter-spacing:.5px}
.ib .val{font-size:18px;font-weight:700;font-family:'IBM Plex Mono',monospace;margin-top:3px}
.ib .sig{font-size:11px;margin-top:2px}
.tb{background:#07101f;border:1px solid #1c2e4a;border-radius:8px;padding:8px;text-align:center}
.tb .lbl{font-size:10px;color:#5d7a9a;text-transform:uppercase}
.tb .val{font-size:14px;font-weight:700;font-family:'IBM Plex Mono',monospace;margin-top:3px}
.stag{display:inline-block;font-size:12px;padding:4px 10px;border-radius:20px;font-weight:600;margin:3px}
.stag.b{background:rgba(5,150,105,.12);color:#059669;border:1px solid rgba(5,150,105,.3)}
.stag.s{background:rgba(220,38,38,.12);color:#dc2626;border:1px solid rgba(220,38,38,.3)}
.ring{width:68px;height:68px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;border:3px solid;font-size:22px;font-weight:700;
  font-family:'IBM Plex Mono',monospace;flex-shrink:0}
.ring.h{color:#059669;border-color:#059669;background:rgba(5,150,105,.1)}
.ring.m{color:#d97706;border-color:#d97706;background:rgba(217,119,6,.1)}
.ring.l{color:#dc2626;border-color:#dc2626;background:rgba(220,38,38,.1)}
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────
def fmt(v, d=2):
    if v is None or v == 0 or (isinstance(v, float) and np.isnan(v)):
        return "--"
    return f"{v:,.{d}f}"

def pstr(v, d=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "--"
    return f"{'+'if v>=0 else ''}{v:.{d}f}%"

def sig_th(s): return {"buy":"ซื้อ","sell":"ขาย","watch":"เฝ้าระวัง","hold":"ถือ"}.get(s,"ถือ")
def sig_ic(s): return {"buy":"🟢","sell":"🔴","watch":"🟡","hold":"⚪"}.get(s,"⚪")
def sc_cl(s):  return "h" if s>=65 else "m" if s>=45 else "l"
def sc_co(s):  return "#059669" if s>=65 else "#d97706" if s>=45 else "#dc2626"
def ema_f(s, p):
    try: return float(s.ewm(span=p, adjust=False).mean().iloc[-1])
    except: return 0.0


# ── Indicator calculation ─────────────────────────────────────
def calc_ind(df):
    if df is None or len(df) < 30:
        return {}
    c = df["close"].astype(float)
    h = df["high"].astype(float)
    lo = df["low"].astype(float)
    v = df["volume"].astype(float)
    n = len(c)
    last = float(c.iloc[-1])

    def sma(s, p): return float(s.rolling(p).mean().iloc[-1]) if len(s) >= p else last

    sma20  = sma(c, 20)
    sma50  = sma(c, min(50, n))
    sma200 = sma(c, min(200, n))
    em12   = ema_f(c, 12)
    em26   = ema_f(c, 26)
    macd_l = em12 - em26
    # simplified macd signal
    macd_s = ema_f(
        pd.Series([ema_f(c.iloc[max(0,i-25):i+1], 12) - ema_f(c.iloc[max(0,i-25):i+1], 26)
                   for i in range(n)]), 9)
    macd_h = macd_l - macd_s

    d   = c.diff()
    rsi = 100 - 100 / (1 + float(d.clip(lower=0).rolling(14).mean().iloc[-1]) /
                       (float((-d.clip(upper=0)).rolling(14).mean().iloc[-1]) + 1e-9))

    bb_m  = sma(c, 20)
    bb_s  = float(c.rolling(20).std().iloc[-1])
    bb_u  = bb_m + 2*bb_s
    bb_dn = bb_m - 2*bb_s
    bb_p  = (last - bb_dn) / (bb_u - bb_dn + 1e-9)

    hh14  = float(h.rolling(14).max().iloc[-1])
    ll14  = float(lo.rolling(14).min().iloc[-1])
    stoch = (last - ll14) / (hh14 - ll14 + 1e-9) * 100

    tr   = pd.concat([h-lo, (h-c.shift()).abs(), (lo-c.shift()).abs()], axis=1).max(axis=1)
    atr  = float(tr.rolling(14).mean().iloc[-1])
    dmp  = (h-h.shift()).clip(lower=0)
    dmm  = (lo.shift()-lo).clip(lower=0)
    dmp2 = dmp.where(dmp>dmm, 0)
    dmm2 = dmm.where(dmm>dmp, 0)
    a14  = tr.rolling(14).mean()
    dip  = float((dmp2.rolling(14).mean()/(a14+1e-9)*100).iloc[-1])
    dim  = float((dmm2.rolling(14).mean()/(a14+1e-9)*100).iloc[-1])
    adx  = float(pd.Series([abs(dip-dim)/(dip+dim+1e-9)*100]).iloc[-1])

    tp   = (h+lo+c)/3
    vwap = float((tp*v).rolling(20).sum().iloc[-1] / (v.rolling(20).sum().iloc[-1]+1e-9))
    vol_r = float(v.iloc[-1] / (v.rolling(20).mean().iloc[-1]+1))

    w    = min(252, n)
    h52  = float(h.rolling(w).max().iloc[-1])
    l52  = float(lo.rolling(w).min().iloc[-1])

    ph   = float(h.iloc[-2]) if n>1 else last
    pl   = float(lo.iloc[-2]) if n>1 else last
    pc   = float(c.iloc[-2]) if n>1 else last
    pvt  = (ph+pl+pc)/3
    rng  = ph-pl

    return dict(
        price=last, chg=(last/float(c.iloc[-2])-1)*100 if n>1 else 0,
        chg5=(last/float(c.iloc[-6])-1)*100 if n>5 else 0,
        sma20=sma20, sma50=sma50, sma200=sma200,
        rsi=rsi, macd=macd_h, bb_pct=bb_p, bb_up=bb_u, bb_dn=bb_dn,
        stoch=stoch, adx=adx, dip=dip, dim=dim,
        vwap=vwap, vol_r=vol_r, atr=atr, h52=h52, l52=l52,
        pivot=pvt, r1=2*pvt-pl, r2=pvt+rng, s1=2*pvt-ph, s2=pvt-rng,
    )


# ── Scoring ───────────────────────────────────────────────────
def score(I, os=35, ob=65):
    if not I: return {}
    sc=50; bs=[]; ss=[]; ns=[]
    p=I.get("price",0)

    r=I.get("rsi",50)
    if r<os:   sc+=8;  bs.append(f"RSI {r:.1f} Oversold")
    elif r>ob: sc-=8;  ss.append(f"RSI {r:.1f} Overbought")
    else:      ns.append(f"RSI {r:.1f} ปกติ")

    m=I.get("macd",0)
    if m>0: sc+=7; bs.append("MACD บวก momentum ขาขึ้น")
    elif m<0: sc-=7; ss.append("MACD ลบ momentum ขาลง")

    s20,s50,s200=I.get("sma20",p),I.get("sma50",p),I.get("sma200",p)
    if p>s20>s50:   sc+=6; bs.append("ราคา > SMA20 > SMA50")
    elif p<s20<s50: sc-=6; ss.append("ราคา < SMA20 < SMA50")
    if s200>0:
        if p>s200: sc+=4; bs.append("เหนือ SMA200")
        else:      sc-=4; ss.append("ต่ำกว่า SMA200")

    bp=I.get("bb_pct",0.5)
    if bp<0.15: sc+=6; bs.append("BB% ใกล้ Lower Oversold")
    elif bp>0.85: sc-=5; ss.append("BB% ใกล้ Upper Overbought")
    if p>I.get("bb_up",p): sc+=3; bs.append("Breakout เหนือ BB Upper")

    st2=I.get("stoch",50)
    if st2<20: sc+=5; bs.append("Stochastic Oversold")
    elif st2>80: sc-=5; ss.append("Stochastic Overbought")

    ax,dp2,dm2=I.get("adx",0),I.get("dip",25),I.get("dim",25)
    if ax>25:
        if dp2>dm2: sc+=5; bs.append(f"ADX {ax:.0f} uptrend แข็ง")
        else: sc-=5; ss.append(f"ADX {ax:.0f} downtrend")
    else: ns.append(f"ADX {ax:.0f} sideways")

    vw=I.get("vwap",p)
    if p>vw: sc+=3; bs.append("ราคา > VWAP")
    else: sc-=3; ss.append("ราคา < VWAP")

    vr=I.get("vol_r",1)
    if vr>1.5: sc+=3; bs.append(f"Volume {vr:.1f}x")
    elif vr<0.5: ns.append("Volume ต่ำ")

    sc=int(max(0,min(100,sc)))
    sig="buy" if sc>=65 else "sell" if sc<=35 else "watch" if sc>=55 else "hold"
    at=I.get("atr",p*0.02) or p*0.02
    en=round(p*0.985,2); t1=round(p+at*2,2); t2=round(p+at*3.5,2); sl=round(p-at*1.5,2)
    up=round(((t1/p)-1)*100,1) if p>0 else 0
    dn=round(((p/sl)-1)*100,1) if sl>0 else 1
    rr=round(up/dn,2) if dn>0 else 0
    return dict(sc=sc,sig=sig,bs=bs,ss=ss,ns=ns,entry=en,t1=t1,t2=t2,sl=sl,up=up,dn=dn,rr=rr)


# ── Settrade helpers ──────────────────────────────────────────
def st_candles(sym, mkt_api, limit=365):
    try:
        data = mkt_api.get_candlestick(sym, interval="1d", limit=limit)
        if not data: return None
        df = pd.DataFrame(data)
        rename = {}
        for col in df.columns:
            cl = col.lower()
            if any(x in cl for x in ["close","last"]): rename[col]="close"
            elif "open" in cl or cl=="o": rename[col]="open"
            elif "high" in cl or cl=="h": rename[col]="high"
            elif "low"  in cl or cl=="l": rename[col]="low"
            elif "vol"  in cl or cl=="v": rename[col]="volume"
        df = df.rename(columns=rename)
        for c in ["open","high","low","close","volume"]:
            if c not in df.columns: df[c]=0
        return df[["open","high","low","close","volume"]].apply(pd.to_numeric, errors="coerce").dropna()
    except: return None

def st_quote(sym, rt_api):
    try:
        q = rt_api.get_quote_symbol(sym)
        return q or {}
    except: return {}

def st_portfolio(inv):
    try:
        port = inv.Portfolio()
        return dict(
            balance=port.get_account_balance(),
            holdings=port.get_portfolio(),
            orders=port.get_orders(),
        )
    except Exception as e:
        return {"error": str(e)}


# ── yfinance helpers ──────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def yf_data(ticker, period="1y"):
    if not YF_OK: return None
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df is None or len(df)<30: return None
        df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
        return df[["open","high","low","close","volume"]].dropna()
    except: return None

@st.cache_data(ttl=3600, show_spinner=False)
def yf_info(ticker):
    if not YF_OK: return {}
    try: return yf.Ticker(ticker).info or {}
    except: return {}


# ── AI News Analysis — รองรับทั้ง Gemini และ Claude ──────────
def build_analysis_prompt(sym, mkt, I, S, cur):
    mkt_th  = {"SET":"ตลาดหุ้นไทย SET","US":"ตลาด NASDAQ/NYSE","CN":"ตลาด NYSE CN ADR"}
    sig_map = {"buy":"ซื้อ","sell":"ขาย","watch":"เฝ้าระวัง","hold":"ถือ"}
    return (
        f"วิเคราะห์หุ้น {sym} ({mkt_th.get(mkt,mkt)}) อย่างละเอียด:\n\n"
        f"1. ค้นหาข่าวสำคัญในรอบ 1 ปีที่ผ่านมาที่กระทบราคาหุ้น "
        f"แต่ละข่าวระบุว่า บวก/ลบ/กลาง และอธิบายผลกระทบ\n"
        f"2. ปัจจัยพื้นฐาน แนวโน้มธุรกิจ คู่แข่ง ความเสี่ยงเชิงธุรกิจ\n"
        f"3. สรุปสัญญาณเทคนิค:\n"
        f"   - ราคา = {cur}{fmt(I.get('price',0))}\n"
        f"   - RSI = {I.get('rsi',50):.1f}  |  MACD Hist = {I.get('macd',0):.4f}\n"
        f"   - BB% = {I.get('bb_pct',0.5):.2f}  |  Stochastic = {I.get('stoch',50):.1f}\n"
        f"   - ADX = {I.get('adx',0):.1f}  |  Vol Ratio = {I.get('vol_r',1):.2f}x\n"
        f"   - คะแนนรวม = {S.get('sc',50)}/100  |  สัญญาณ = {sig_map.get(S.get('sig','hold'),'ถือ')}\n"
        f"4. คำแนะนำ:\n"
        f"   - จุดซื้อ = {cur}{S.get('entry',0)}\n"
        f"   - เป้าหมาย 1 = {cur}{S.get('t1',0)}\n"
        f"   - เป้าหมาย 2 = {cur}{S.get('t2',0)}\n"
        f"   - Stop Loss = {cur}{S.get('sl',0)}\n"
        f"   - Risk/Reward = 1:{S.get('rr',0)}\n"
        f"5. ความเสี่ยงสำคัญที่นักลงทุนควรระวัง\n\n"
        f"ตอบภาษาไทย กระชับ ได้ใจความ"
    )


def analyze_with_gemini(sym, mkt, I, S, cur, api_key):
    """วิเคราะห์ด้วย Gemini API (Google Search grounding)"""
    prompt = build_analysis_prompt(sym, mkt, I, S, cur)
    # Gemini 1.5 Pro with Google Search tool
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent?key=" + api_key
    )
    body = {
        "contents": [{"role":"user","parts":[{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
        }
    }
    r = requests.post(url, headers={"Content-Type":"application/json"},
                      json=body, timeout=90)
    r.raise_for_status()
    data = r.json()
    # Extract text from candidates
    txt = ""
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            if "text" in part:
                txt += part["text"]
    return txt.strip() or "ไม่ได้รับผลลัพธ์จาก Gemini"


def analyze_with_claude(sym, mkt, I, S, cur):
    """วิเคราะห์ด้วย Claude API (web search)"""
    prompt = build_analysis_prompt(sym, mkt, I, S, cur)
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"Content-Type":"application/json"},
        json={"model":"claude-sonnet-4-20250514","max_tokens":1800,
              "tools":[{"type":"web_search_20250305","name":"web_search"}],
              "messages":[{"role":"user","content":prompt}]},
        timeout=90)
    r.raise_for_status()
    return "".join(b["text"] for b in r.json().get("content",[])
                   if b.get("type")=="text").strip()


def run_analysis(sym, mkt, I, S, cur):
    """เลือก AI provider จาก session state"""
    provider = st.session_state.get("ai_provider","gemini")
    if provider == "gemini":
        key = st.session_state.get("gemini_key","").strip()
        if not key:
            return "❌ กรุณาใส่ Gemini API Key ใน sidebar ก่อน"
        try:
            return analyze_with_gemini(sym, mkt, I, S, cur, key)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 400:
                err = e.response.json()
                return f"❌ Gemini error: {err.get('error',{}).get('message', str(e))}"
            return f"❌ Gemini HTTP error: {e}"
        except Exception as e:
            return f"❌ Gemini error: {e}"
    else:
        try:
            return analyze_with_claude(sym, mkt, I, S, cur)
        except Exception as e:
            return f"❌ Claude error: {e}"


# ── Stock universe ────────────────────────────────────────────
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
MARKETS = {
    "SET50 🇹🇭":  {"stocks":SET50,   "cur":"฿","src":"settrade"},
    "US Tech 🇺🇸": {"stocks":US_TECH, "cur":"$","src":"yfinance"},
    "CN Tech 🇨🇳": {"stocks":CN_TECH, "cur":"$","src":"yfinance"},
}


# ── Session state init ────────────────────────────────────────
for k,v in [("st_ok",False),("st_mkt",None),("st_rt",None),("st_inv",None),
            ("rt_list",[("ADVANC","SET"),("PTT","SET"),("NVDA","US")])]:
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ ตั้งค่า")

    # ── AI Provider ──
    st.markdown("### 🤖 AI วิเคราะห์ข่าว")
    ai_provider = st.radio(
        "เลือก AI",
        ["gemini", "claude"],
        format_func=lambda x: "Gemini (Google)" if x=="gemini" else "Claude (Anthropic)",
        key="ai_provider",
        horizontal=True,
    )
    if ai_provider == "gemini":
        gemini_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="AIza...",
            key="gemini_key",
            help="รับ key ฟรีที่ aistudio.google.com",
        )
        if gemini_key:
            st.success("✅ Gemini key พร้อม")
        else:
            st.info("รับ API Key ฟรีที่\naistudio.google.com/apikey")
    else:
        st.caption("ใช้ Claude API built-in ไม่ต้องใส่ key เพิ่ม")

    st.markdown("---")

    # ── Settrade login ──
    st.markdown("### Settrade API")
    if st.session_state.st_ok:
        st.success("✅ เชื่อมต่อแล้ว")
        if st.button("ออกจากระบบ"):
            st.session_state.update(st_ok=False, st_mkt=None, st_rt=None, st_inv=None)
            st.rerun()
    else:
        with st.form("login_form"):
            app_id     = st.text_input("APP_ID")
            app_secret = st.text_input("APP_SECRET", type="password")
            app_code   = st.text_input("APP_CODE",  value="SANDBOX")
            broker_id  = st.text_input("BROKER_ID", value="SANDBOX")
            submitted  = st.form_submit_button("🔗 เชื่อมต่อ")
            if submitted:
                if not SETTRADE_OK:
                    st.error("settrade_v2 ไม่ได้ติดตั้ง\nตรวจ requirements.txt")
                elif not app_id or not app_secret:
                    st.error("กรอก APP_ID และ APP_SECRET")
                else:
                    try:
                        inv = Investor(
                            app_id=app_id.strip(),
                            app_secret=app_secret.strip(),
                            app_code=app_code.strip(),
                            broker_id=broker_id.strip(),
                        )
                        mkt_api = inv.Market()
                        rt_api  = inv.Realtime()
                        test = mkt_api.get_candlestick("PTT", interval="1d", limit=3)
                        if test:
                            st.session_state.update(st_ok=True, st_mkt=mkt_api,
                                                    st_rt=rt_api, st_inv=inv)
                            st.success("✅ เชื่อมต่อสำเร็จ!")
                            st.rerun()
                        else:
                            st.error("เชื่อมต่อได้แต่ดึงข้อมูลไม่ได้")
                    except Exception as e:
                        st.error(f"เชื่อมต่อไม่สำเร็จ:\n{e}")

    st.markdown("---")
    st.markdown("### Parameters")
    rsi_os = st.slider("RSI Oversold",   15, 45, 35)
    rsi_ob = st.slider("RSI Overbought", 55, 85, 65)
    min_sc = st.slider("คะแนนขั้นต่ำ", 0, 100, 55)
    min_rr = st.slider("R/R ขั้นต่ำ",   0.5, 3.0, 1.2, step=0.1)

    st.markdown("---")
    st.caption(f"settrade_v2: {'✅' if SETTRADE_OK else '❌ ต้องติดตั้ง'}")
    st.caption(f"yfinance: {'✅' if YF_OK else '❌ ต้องติดตั้ง'}")


# ── Main header ───────────────────────────────────────────────
st.markdown("""
<div style="padding:18px 0 8px;text-align:center">
  <div style="font-size:26px;font-weight:700">📈 Stock Pro</div>
  <div style="font-size:13px;color:#5d7a9a;margin-top:4px">
    Settrade Real-time · SET50 · US Tech · CN Tech · AI วิเคราะห์
  </div>
</div>
""", unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🔍 สแกนหุ้น","📊 วิเคราะห์","📡 Real-time","💼 Portfolio"])


# ══════════════════════════════════════════════════════════════
# TAB 1: SCANNER
# ══════════════════════════════════════════════════════════════
with t1:
    ca, cb = st.columns(2)
    with ca: mkt_sel = st.selectbox("ตลาด", list(MARKETS.keys()), key="sc_mkt")
    with cb: sig_sel = st.selectbox("สัญญาณ", ["ทั้งหมด","ซื้อ","ซื้อ+เฝ้าระวัง","ขาย"], key="sc_sig")

    cfg = MARKETS[mkt_sel]
    stocks, cur, src = cfg["stocks"], cfg["cur"], cfg["src"]
    allowed = {"ทั้งหมด":["buy","sell","watch","hold"],"ซื้อ":["buy"],
               "ซื้อ+เฝ้าระวัง":["buy","watch"],"ขาย":["sell"]}[sig_sel]

    if src=="settrade" and not st.session_state.st_ok:
        st.warning("⚠️ SET50 ต้องเชื่อมต่อ Settrade ก่อน (sidebar ด้านซ้าย)\nหรือเลือก US Tech / CN Tech ที่ใช้ yfinance")
    else:
        if st.button(f"🔍 สแกน {mkt_sel} ({len(stocks)} ตัว)"):
            results = []
            pb = st.progress(0, text="กำลังสแกน...")
            st_txt = st.empty()
            for i, (sym, name) in enumerate(stocks):
                st_txt.text(f"สแกน {sym} ({i+1}/{len(stocks)})...")
                try:
                    if src == "settrade":
                        df = st_candles(sym, st.session_state.st_mkt, 365)
                        q  = st_quote(sym, st.session_state.st_rt)
                        if df is not None and q:
                            rp = float(q.get("last", q.get("close", 0)))
                            if rp > 0:
                                df.iloc[-1, df.columns.get_loc("close")] = rp
                    else:
                        df = yf_data(sym)
                    I = calc_ind(df)
                    if not I or I.get("price",0) <= 0: continue
                    S = score(I, rsi_os, rsi_ob)
                    if S.get("sc",0) >= min_sc and S.get("rr",0) >= min_rr and S.get("sig") in allowed:
                        results.append((sym,name,cur,I,S))
                except Exception as e:
                    st.warning(f"Skip {sym}: {e}")
                pb.progress((i+1)/len(stocks))
            pb.empty(); st_txt.empty()
            results.sort(key=lambda x:-x[4]["sc"])
            st.success(f"พบ **{len(results)}** หุ้น จาก {len(stocks)} ตัว")

            for sym,name,cur2,I,S in results:
                up_c = "#059669" if I["chg"]>=0 else "#dc2626"
                lc   = {"buy":"buy","sell":"sell","watch":"watch"}.get(S["sig"],"")
                st.markdown(f"""
                <div class="sc {lc}">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
                    <div>
                      <div class="sym-lg">{sym} <span style="font-size:13px;color:#5d7a9a;font-family:'Sarabun',sans-serif">{name}</span></div>
                      <div style="margin-top:8px">{sig_ic(S['sig'])} <b style="color:#dce8f5">{sig_th(S['sig'])}</b>
                        <span style="font-size:12px;color:#5d7a9a;margin-left:8px">R/R 1:{S['rr']}</span></div>
                    </div>
                    <div style="text-align:right">
                      <div class="px-lg" style="color:{up_c}">{cur2}{fmt(I['price'])}</div>
                      <div style="font-size:14px;color:{up_c};font-weight:700">{pstr(I['chg'])}</div>
                      <div style="font-size:22px;font-weight:700;color:{sc_co(S['sc'])};font-family:'IBM Plex Mono',monospace;margin-top:4px">{S['sc']}</div>
                    </div>
                  </div>
                  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:7px;margin-bottom:10px">
                    <div class="ib"><div class="lbl">RSI</div><div class="val {'bull' if I['rsi']<rsi_os else 'bear' if I['rsi']>rsi_ob else ''}">{I['rsi']:.1f}</div></div>
                    <div class="ib"><div class="lbl">ADX</div><div class="val {'bull' if I['adx']>25 and I['dip']>I['dim'] else 'bear' if I['adx']>25 and I['dim']>I['dip'] else ''}">{I['adx']:.1f}</div></div>
                    <div class="ib"><div class="lbl">BB%</div><div class="val {'bull' if I['bb_pct']<0.2 else 'bear' if I['bb_pct']>0.8 else ''}">{I['bb_pct']:.2f}</div></div>
                    <div class="ib"><div class="lbl">Vol</div><div class="val {'bull' if I['vol_r']>1.5 else ''}">{I['vol_r']:.1f}x</div></div>
                  </div>
                  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:7px">
                    <div class="tb"><div class="lbl">จุดซื้อ</div><div class="val" style="color:#3b82f6">{cur2}{fmt(S['entry'])}</div></div>
                    <div class="tb"><div class="lbl">เป้า 1</div><div class="val" style="color:#059669">{cur2}{fmt(S['t1'])}</div></div>
                    <div class="tb"><div class="lbl">เป้า 2</div><div class="val" style="color:#34d399">{cur2}{fmt(S['t2'])}</div></div>
                    <div class="tb"><div class="lbl">Stop</div><div class="val" style="color:#dc2626">{cur2}{fmt(S['sl'])}</div></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"วิเคราะห์ {sym} เจาะลึก →", key=f"da_{sym}"):
                    st.session_state["da_sym"] = sym
                    st.session_state["da_mkt"] = "SET" if "SET" in mkt_sel else ("US" if "US" in mkt_sel else "CN")
                    st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB 2: DEEP ANALYSIS
# ══════════════════════════════════════════════════════════════
with t2:
    ca2, cb2 = st.columns([3,1])
    with ca2:
        sym_in = st.text_input("ชื่อหุ้น", value=st.session_state.get("da_sym",""),
                               placeholder="เช่น ADVANC, PTT, NVDA, BABA")
    with cb2:
        mkt_in = st.selectbox("ตลาด", ["SET","US","CN"],
                              index=["SET","US","CN"].index(st.session_state.get("da_mkt","SET")))

    if st.button("📊 วิเคราะห์เจาะลึก"):
        sym2 = sym_in.strip().upper()
        cur2 = "฿" if mkt_in=="SET" else "$"
        if not sym2:
            st.warning("กรุณาใส่ชื่อหุ้น")
        elif mkt_in=="SET" and not st.session_state.st_ok:
            st.error("ต้องเชื่อมต่อ Settrade ก่อน")
        else:
            with st.spinner(f"กำลังดึงข้อมูล {sym2}..."):
                q2 = {}
                if mkt_in == "SET":
                    df2 = st_candles(sym2, st.session_state.st_mkt, 365)
                    q2  = st_quote(sym2, st.session_state.st_rt)
                    if df2 is not None and q2:
                        rp = float(q2.get("last", q2.get("close", 0)))
                        if rp > 0:
                            df2.iloc[-1, df2.columns.get_loc("close")] = rp
                else:
                    df2 = yf_data(sym2)
                I2 = calc_ind(df2)
                if not I2 or I2.get("price",0)<=0:
                    st.error(f"ดึงข้อมูล {sym2} ไม่ได้"); st.stop()
                S2 = score(I2, rsi_os, rsi_ob)

            p2   = I2["price"]
            up_c = "#059669" if I2["chg"]>=0 else "#dc2626"
            p52p = max(0,min(100,(p2-I2["l52"])/(I2["h52"]-I2["l52"]+1e-9)*100))

            # Fundamental (US/CN only)
            info2 = {}
            if mkt_in in ("US","CN"):
                with st.spinner("ดึง fundamental..."): info2 = yf_info(sym2)
            name2 = info2.get("longName", info2.get("shortName", sym2))

            # Header
            st.markdown(f"""
            <div class="sc">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px">
                <div>
                  <div style="font-size:26px;font-weight:700;font-family:'IBM Plex Mono',monospace">{sym2}</div>
                  <div style="font-size:13px;color:#5d7a9a;margin-top:3px">{name2} &middot; {mkt_in}</div>
                  <div style="margin-top:10px">{sig_ic(S2['sig'])} <b style="font-size:16px;color:#dce8f5">{sig_th(S2['sig'])}</b></div>
                  {('<div style="font-size:13px;color:#5d7a9a;margin-top:4px">Real-time: ฿'+fmt(float(q2.get("last",0)))+'</div>') if q2 else ""}
                </div>
                <div class="ring {sc_cl(S2['sc'])}">{S2['sc']}</div>
              </div>
              <div class="px-xl" style="color:{up_c}">{cur2}{fmt(p2)}</div>
              <div style="font-size:15px;color:{up_c};font-weight:700;margin-top:5px">
                {pstr(I2['chg'])} วันนี้
                <span style="color:#5d7a9a;font-weight:400"> &nbsp; {pstr(I2['chg5'],1)} 5 วัน</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Fundamental metrics
            if info2:
                f1,f2,f3,f4,f5,f6 = st.columns(6)
                pe=info2.get("trailingPE"); pb2=info2.get("priceToBook")
                roe=info2.get("returnOnEquity"); mc=info2.get("marketCap")
                dy=info2.get("dividendYield"); beta=info2.get("beta")
                for col,lbl,val in [
                    (f1,"P/E",     f"{pe:.1f}" if pe else "N/A"),
                    (f2,"P/B",     f"{pb2:.2f}" if pb2 else "N/A"),
                    (f3,"ROE",     f"{roe*100:.1f}%" if roe else "N/A"),
                    (f4,"Mkt Cap", f"${mc/1e9:.1f}B" if mc else "N/A"),
                    (f5,"Div Yld", f"{dy*100:.2f}%" if dy else "N/A"),
                    (f6,"Beta",    f"{beta:.2f}" if beta else "N/A"),
                ]:
                    with col: st.metric(lbl, val)

            # Indicators 2×4
            st.markdown("#### Indicators")
            ci = st.columns(4)
            for idx,(lbl,val,bull,bear) in enumerate([
                ("RSI (14)",  f"{I2['rsi']:.1f}",        I2['rsi']<rsi_os,                          I2['rsi']>rsi_ob),
                ("MACD Hist", f"{I2['macd']:.4f}",        I2['macd']>0,                              I2['macd']<0),
                ("BB %B",     f"{I2['bb_pct']:.2f}",      I2['bb_pct']<0.2,                          I2['bb_pct']>0.8),
                ("Stoch %K",  f"{I2['stoch']:.1f}",       I2['stoch']<20,                            I2['stoch']>80),
                ("ADX",       f"{I2['adx']:.1f}",         I2['adx']>25 and I2['dip']>I2['dim'],      I2['adx']>25 and I2['dim']>I2['dip']),
                ("Vol Ratio", f"{I2['vol_r']:.2f}x",      I2['vol_r']>1.5,                           I2['vol_r']<0.5),
                ("vs SMA50",  pstr((p2/I2['sma50']-1)*100 if I2['sma50'] else 0,1), p2>I2['sma50'], p2<I2['sma50']),
                ("VWAP",      f"{cur2}{fmt(I2['vwap'])}",  p2>I2['vwap'],                            p2<I2['vwap']),
            ]):
                with ci[idx%4]:
                    c = "bull" if bull else "bear" if bear else "neut"
                    b = "▲ Bullish" if bull else "▼ Bearish" if bear else "→ Neutral"
                    st.markdown(f'<div class="ib"><div class="lbl">{lbl}</div>'
                                f'<div class="val {c}">{val}</div>'
                                f'<div class="sig {c}">{b}</div></div>', unsafe_allow_html=True)

            # Targets
            st.markdown("#### 🎯 ราคาเป้าหมาย")
            t2c1,t2c2,t2c3,t2c4 = st.columns(4)
            for col,lbl,val,co in [
                (t2c1,"จุดซื้อ",   f"{cur2}{fmt(S2['entry'])}","#3b82f6"),
                (t2c2,"เป้า 1",    f"{cur2}{fmt(S2['t1'])}",   "#059669"),
                (t2c3,"เป้า 2",    f"{cur2}{fmt(S2['t2'])}",   "#34d399"),
                (t2c4,"Stop Loss", f"{cur2}{fmt(S2['sl'])}",   "#dc2626"),
            ]:
                with col:
                    st.markdown(f'<div class="tb"><div class="lbl">{lbl}</div>'
                                f'<div class="val" style="color:{co}">{val}</div></div>',
                                unsafe_allow_html=True)

            rr_c = "#059669" if S2["rr"]>=2 else "#d97706" if S2["rr"]>=1.5 else "#dc2626"
            st.markdown(f"""
            <div style="background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.2);
              border-radius:10px;padding:12px 16px;margin-top:10px;
              display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:14px;color:#5d7a9a">Risk / Reward</span>
              <span style="font-size:22px;font-weight:700;font-family:'IBM Plex Mono',monospace;color:{rr_c}">
                1 : {S2['rr']}</span>
            </div>
            """, unsafe_allow_html=True)

            # Pivot
            st.markdown("#### Pivot Points")
            pvc = st.columns(5)
            for col,lbl,val,co in [
                (pvc[0],"R2",    f"{cur2}{fmt(I2['r2'])}", "#f87171"),
                (pvc[1],"R1",    f"{cur2}{fmt(I2['r1'])}", "#fb923c"),
                (pvc[2],"Pivot", f"{cur2}{fmt(I2['pivot'])}", "#60a5fa"),
                (pvc[3],"S1",    f"{cur2}{fmt(I2['s1'])}", "#34d399"),
                (pvc[4],"S2",    f"{cur2}{fmt(I2['s2'])}", "#059669"),
            ]:
                with col:
                    st.markdown(f'<div class="tb"><div class="lbl">{lbl}</div>'
                                f'<div class="val" style="color:{co}">{val}</div></div>',
                                unsafe_allow_html=True)

            # 52W
            st.markdown("#### 52-Week Range")
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;font-size:12px;color:#5d7a9a;margin-bottom:5px">
              <span>Low {cur2}{fmt(I2['l52'])}</span>
              <span style="color:#dce8f5;font-weight:700">{p52p:.0f}% จากต่ำสุด</span>
              <span>High {cur2}{fmt(I2['h52'])}</span>
            </div>
            """, unsafe_allow_html=True)
            st.progress(p52p/100)

            # Signals
            if S2["bs"] or S2["ss"]:
                st.markdown("#### สัญญาณ")
                html = ""
                for s in S2["bs"]: html += f'<span class="stag b">▲ {s}</span>'
                for s in S2["ss"]: html += f'<span class="stag s">▼ {s}</span>'
                st.markdown(html, unsafe_allow_html=True)

            # AI News
            st.markdown("---")
            st.markdown("#### 📰 AI วิเคราะห์ + ข่าวสำคัญ 1 ปี")
            provider_label = "Gemini" if st.session_state.get("ai_provider","gemini")=="gemini" else "Claude"
            with st.spinner(f"{provider_label} กำลังค้นข่าวและวิเคราะห์..."):
                news = run_analysis(sym2, mkt_in, I2, S2, cur2)
            st.markdown(news)


# ══════════════════════════════════════════════════════════════
# TAB 3: REAL-TIME
# ══════════════════════════════════════════════════════════════
with t3:
    st.markdown("### 📡 Real-time Watchlist")
    st.caption("SET = Settrade real-time จริง · US/CN = yfinance (delay 15 นาที)")

    ca3,cb3,cc3 = st.columns([2,1,1])
    with ca3: ns = st.text_input("Ticker", placeholder="เช่น KBANK, AAPL", label_visibility="collapsed", key="rt_in")
    with cb3: nm = st.selectbox("", ["SET","US","CN"], label_visibility="collapsed", key="rt_mkt")
    with cc3:
        if st.button("+ เพิ่ม"):
            s3 = ns.strip().upper()
            if s3 and (s3,nm) not in st.session_state.rt_list:
                st.session_state.rt_list.append((s3,nm)); st.rerun()

    rc1,rc2 = st.columns(2)
    with rc1: do_ref = st.button("🔄 Refresh")
    with rc2:
        if st.button("🗑️ ล้างทั้งหมด"):
            st.session_state.rt_list = []; st.rerun()

    for sym3,mkt3 in st.session_state.rt_list:
        cur3 = "฿" if mkt3=="SET" else "$"
        price3=chg3=rsi3=s20_3=e12_3=e26_3=0

        try:
            if mkt3=="SET" and st.session_state.st_ok:
                q3  = st_quote(sym3, st.session_state.st_rt)
                df3 = st_candles(sym3, st.session_state.st_mkt, 60)
                if q3: price3=float(q3.get("last",q3.get("close",0))); chg3=float(q3.get("change_percent",q3.get("chg_pct",0)))
                if df3 is not None and price3>0:
                    df3.iloc[-1,df3.columns.get_loc("close")]=price3
                    I3=calc_ind(df3)
                    if I3: rsi3=I3["rsi"]; s20_3=I3["sma20"]; e12_3=ema_f(df3["close"],12); e26_3=ema_f(df3["close"],26)
            elif mkt3 in ("US","CN"):
                df3=yf_data(sym3,"3mo")
                if df3 is not None and len(df3)>1:
                    price3=float(df3["close"].iloc[-1])
                    chg3=(price3/float(df3["close"].iloc[-2])-1)*100
                    I3=calc_ind(df3)
                    if I3: rsi3=I3["rsi"]; s20_3=I3["sma20"]; e12_3=ema_f(df3["close"],12); e26_3=ema_f(df3["close"],26)
        except: pass

        sc3=50
        if rsi3<35: sc3+=10
        elif rsi3>65: sc3-=10
        if e12_3>e26_3: sc3+=8
        else: sc3-=8
        if price3>s20_3: sc3+=6
        else: sc3-=6
        sc3=max(0,min(100,sc3))
        sig3="buy" if sc3>=65 else "sell" if sc3<=35 else "watch" if sc3>=55 else "hold"
        up_c3="#059669" if chg3>=0 else "#dc2626"

        cc_w,cc_rm = st.columns([10,1])
        with cc_w:
            lc3={"buy":"buy","sell":"sell","watch":"watch"}.get(sig3,"")
            st.markdown(f"""
            <div class="sc {lc3}">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                  <span style="font-size:18px;font-weight:700;font-family:'IBM Plex Mono',monospace">{sym3}</span>
                  <span style="font-size:13px;color:#5d7a9a;margin-left:8px">{mkt3}</span>
                  <div style="margin-top:6px">{sig_ic(sig3)} <b style="color:#dce8f5">{sig_th(sig3)}</b>
                    <span style="font-size:12px;color:#5d7a9a;margin-left:8px">Score {sc3}</span></div>
                </div>
                <div style="text-align:right">
                  <div style="font-size:22px;font-weight:700;font-family:'IBM Plex Mono',monospace;color:{up_c3}">
                    {cur3}{fmt(price3) if price3 else '--'}</div>
                  <div style="font-size:13px;color:{up_c3};font-weight:700">{pstr(chg3)}</div>
                </div>
              </div>
              <div style="background:#1c2e4a;border-radius:3px;height:4px;margin-top:10px">
                <div style="width:{sc3}%;height:4px;border-radius:3px;background:{sc_co(sc3)}"></div>
              </div>
              <div style="font-size:12px;color:#5d7a9a;margin-top:5px">
                RSI {rsi3:.0f} · {'EMA bullish' if e12_3>e26_3 else 'EMA bearish'} · {'เหนือ SMA20' if price3>s20_3 else 'ต่ำกว่า SMA20'}
              </div>
            </div>
            """, unsafe_allow_html=True)
        with cc_rm:
            if st.button("✕", key=f"rm_{sym3}_{mkt3}"):
                st.session_state.rt_list.remove((sym3,mkt3)); st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB 4: PORTFOLIO
# ══════════════════════════════════════════════════════════════
with t4:
    st.markdown("### 💼 Portfolio & บัญชี")
    if not st.session_state.st_ok:
        st.warning("เชื่อมต่อ Settrade ก่อน (sidebar ด้านซ้าย)")
    else:
        if st.button("🔄 โหลด Portfolio"):
            inv = st.session_state.st_inv
            port = inv.Portfolio()

            # Balance
            st.markdown("#### 💰 สรุปบัญชี")
            try:
                bal = port.get_account_balance()
                if bal:
                    b = bal[0] if isinstance(bal, list) else bal
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("วงเงินทั้งหมด", f"฿{float(b.get('credit_limit',b.get('line',0))):,.0f}")
                    c2.metric("ใช้ไปแล้ว",     f"฿{float(b.get('used_amount',b.get('call_force_margin',0))):,.0f}")
                    c3.metric("คงเหลือ",        f"฿{float(b.get('available_balance',b.get('net_balance',0))):,.0f}")
                    c4.metric("กำไร/ขาดทุน",   f"฿{float(b.get('unrealized_pl',b.get('unrealized',0))):,.0f}")
            except Exception as e:
                st.info(f"Balance: {e}")

            # Holdings
            st.markdown("#### 📋 หุ้นที่ถืออยู่")
            try:
                h = port.get_portfolio()
                if h:
                    df_h = pd.DataFrame(h if isinstance(h,list) else [h])
                    st.dataframe(df_h, use_container_width=True)
                else: st.info("ไม่มีหุ้นในพอร์ต")
            except Exception as e: st.info(f"Portfolio: {e}")

            # Orders
            st.markdown("#### 📝 คำสั่งซื้อขาย")
            try:
                o = port.get_orders()
                if o:
                    df_o = pd.DataFrame(o if isinstance(o,list) else [o])
                    st.dataframe(df_o, use_container_width=True)
                else: st.info("ไม่มีคำสั่งค้างอยู่")
            except Exception as e: st.info(f"Orders: {e}")

            # Trade history
            st.markdown("#### 📈 ประวัติการซื้อขาย")
            try:
                tr2 = port.get_trades() if hasattr(port, "get_trades") else None
                if tr2:
                    df_t = pd.DataFrame(tr2 if isinstance(tr2,list) else [tr2])
                    st.dataframe(df_t, use_container_width=True)
                else: st.info("ไม่มีข้อมูล trade history")
            except Exception as e: st.info(f"Trades: {e}")

st.markdown('<div style="text-align:center;font-size:11px;color:#1c2e4a;margin-top:24px">'
            'ใช้เพื่อการศึกษาเท่านั้น · ไม่ใช่คำแนะนำการลงทุน</div>',
            unsafe_allow_html=True)
