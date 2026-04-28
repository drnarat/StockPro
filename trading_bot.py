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
# settrade-v2 — optional (ไม่อยู่บน PyPI สาธารณะ ต้องติดตั้งแยก)
# ถ้าไม่มี จะยังใช้ US/CN ผ่าน yfinance ได้ปกติ
SETTRADE_OK = False
try:
    from settrade_v2 import Investor
    SETTRADE_OK = True
except Exception:
    SETTRADE_OK = False

YF_OK = False
try:
    import yfinance as yf
    YF_OK = True
except Exception:
    YF_OK = False

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Pro",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded"
)


# ── Settrade Required ───────────────────────────────────────
if not SETTRADE_OK:
    st.error("❌ settrade-v2 ไม่ได้ติดตั้ง")
    st.info("""
**วิธีแก้ — รันบนเครื่อง Windows แล้วเปิดมือถือผ่าน WiFi:**

```
1. เปิด CMD แล้วพิมพ์:
   pip install settrade-v2 streamlit yfinance

2. รันแอป:
   streamlit run app.py

3. เปิดมือถือ (WiFi เดียวกัน) พิมพ์:
   http://[IP เครื่อง Windows]:8501
```

หา IP: เปิด CMD → พิมพ์ `ipconfig` → ดู IPv4 Address
    """)
    st.stop()

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ━━━━ BASE ━━━━ */
html, body, [class*="css"] {
  font-family: 'Prompt', sans-serif !important;
  font-size: 15px !important;
  color: #0f172a !important;
  background: #f0f4ff !important;
}
footer, #MainMenu, header { visibility: hidden; }
.stApp, section[data-testid="stMain"] {
  background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 50%, #f0fdf4 100%) !important;
  min-height: 100vh;
}

/* ━━━━ BUTTONS ━━━━ */
.stButton > button {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 12px !important;
  padding: 13px 20px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  font-family: 'Prompt', sans-serif !important;
  width: 100% !important;
  letter-spacing: .3px !important;
  box-shadow: 0 4px 12px rgba(99,102,241,.25) !important;
  transition: all .2s !important;
}
.stButton > button:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 16px rgba(99,102,241,.35) !important;
}
.stButton > button:disabled { opacity: .4 !important; box-shadow: none !important; }

/* ━━━━ INPUTS ━━━━ */
.stTextInput input,
.stNumberInput input,
div[data-baseweb="input"] input {
  background: #fff !important;
  color: #0f172a !important;
  border: 1.5px solid #c7d2fe !important;
  border-radius: 10px !important;
  font-size: 15px !important;
  font-family: 'Prompt', sans-serif !important;
  padding: 10px 14px !important;
  box-shadow: 0 1px 3px rgba(99,102,241,.08) !important;
  transition: border-color .2s !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,.12) !important;
}
.stTextInput input::placeholder { color: #a5b4fc !important; }

div[data-baseweb="select"] > div {
  background: #fff !important;
  border: 1.5px solid #c7d2fe !important;
  border-radius: 10px !important;
  color: #0f172a !important;
  box-shadow: 0 1px 3px rgba(99,102,241,.08) !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] div { color: #0f172a !important; }

/* ━━━━ LABELS ━━━━ */
label, p, span, div { color: #0f172a !important; }
.stTextInput label, .stSelectbox label, .stNumberInput label {
  font-weight: 600 !important;
  font-size: 13px !important;
  color: #4f46e5 !important;
  text-transform: uppercase !important;
  letter-spacing: .6px !important;
}

/* ━━━━ TABS ━━━━ */
.stTabs [data-baseweb="tab-list"] {
  background: #e0e7ff !important;
  border-radius: 14px !important;
  padding: 5px !important;
  gap: 3px !important;
  border: 1px solid #c7d2fe !important;
}
.stTabs [data-baseweb="tab"] {
  font-size: 14px !important;
  font-weight: 600 !important;
  padding: 10px 16px !important;
  color: #6366f1 !important;
  font-family: 'Prompt', sans-serif !important;
  border-radius: 10px !important;
  transition: all .2s !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  color: #fff !important;
  box-shadow: 0 4px 10px rgba(99,102,241,.3) !important;
}

/* ━━━━ EXPANDER ━━━━ */
div[data-testid="stExpander"] {
  background: rgba(255,255,255,.8) !important;
  border: 1.5px solid #c7d2fe !important;
  border-radius: 14px !important;
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 12px rgba(99,102,241,.08) !important;
}
div[data-testid="stExpander"] summary {
  color: #4f46e5 !important;
  font-size: 15px !important;
  font-weight: 600 !important;
}

/* ━━━━ METRICS ━━━━ */
div[data-testid="stMetric"] {
  background: rgba(255,255,255,.9) !important;
  border: 1.5px solid #c7d2fe !important;
  border-radius: 12px !important;
  padding: 14px !important;
  box-shadow: 0 2px 8px rgba(99,102,241,.08) !important;
}
div[data-testid="stMetric"] label {
  color: #6366f1 !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: .5px !important;
}
div[data-testid="stMetricValue"] {
  color: #0f172a !important;
  font-size: 22px !important;
  font-weight: 700 !important;
  font-family: 'JetBrains Mono', monospace !important;
}

/* ━━━━ SLIDER ━━━━ */
div[data-testid="stSlider"] label {
  color: #4f46e5 !important;
  font-weight: 600 !important;
  font-size: 13px !important;
}

/* ━━━━ RADIO ━━━━ */
div[data-testid="stRadio"] label,
div[data-testid="stRadio"] p { color: #0f172a !important; font-size: 15px !important; }

/* ━━━━ ALERTS ━━━━ */
div[data-testid="stAlert"] { border-radius: 12px !important; }
div[data-testid="stAlert"] p { color: inherit !important; }

/* ━━━━ CAPTION ━━━━ */
.stCaption, small { color: #818cf8 !important; font-size: 12px !important; }

/* ━━━━ DATAFRAME ━━━━ */
div[data-testid="stDataFrame"] {
  border: 1.5px solid #c7d2fe !important;
  border-radius: 12px !important;
  overflow: hidden !important;
}

/* ━━━━ CUSTOM CARDS ━━━━ */
.sc {
  background: rgba(255,255,255,.85);
  border: 1.5px solid #e0e7ff;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px rgba(99,102,241,.08);
  backdrop-filter: blur(8px);
  transition: box-shadow .2s;
}
.sc:hover { box-shadow: 0 4px 20px rgba(99,102,241,.15); }
.sc.buy   { border-left: 4px solid #10b981; background: rgba(240,253,250,.9); }
.sc.sell  { border-left: 4px solid #ef4444; background: rgba(255,241,242,.9); }
.sc.watch { border-left: 4px solid #f59e0b; background: rgba(255,251,235,.9); }

/* ━━━━ TYPOGRAPHY ━━━━ */
.mono  { font-family: 'JetBrains Mono', monospace !important; }
.bull  { color: #059669 !important; font-weight: 600 !important; }
.bear  { color: #dc2626 !important; font-weight: 600 !important; }
.neut  { color: #d97706 !important; font-weight: 600 !important; }
.dim   { color: #818cf8 !important; }

.px-xl { font-size: 32px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.px-lg { font-size: 22px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.sym-lg{ font-size: 20px; font-weight: 700; font-family: 'JetBrains Mono', monospace; color: #0f172a; }

/* ━━━━ INDICATOR BOX ━━━━ */
.ib {
  background: rgba(255,255,255,.9);
  border: 1.5px solid #e0e7ff;
  border-radius: 10px;
  padding: 10px 8px;
  text-align: center;
  margin-bottom: 7px;
  box-shadow: 0 1px 4px rgba(99,102,241,.06);
}
.ib .lbl {
  font-size: 10px; color: #818cf8 !important;
  text-transform: uppercase; letter-spacing: .8px; font-weight: 600;
}
.ib .val {
  font-size: 18px; font-weight: 700;
  font-family: 'JetBrains Mono', monospace; margin-top: 3px; color: #0f172a;
}
.ib .sig { font-size: 11px; margin-top: 2px; }

/* ━━━━ TARGET BOX ━━━━ */
.tb {
  background: rgba(255,255,255,.9);
  border: 1.5px solid #e0e7ff;
  border-radius: 10px;
  padding: 10px 6px;
  text-align: center;
}
.tb .lbl { font-size: 10px; color: #818cf8 !important; text-transform: uppercase; font-weight: 600; }
.tb .val { font-size: 14px; font-weight: 700; font-family: 'JetBrains Mono', monospace; margin-top: 3px; }

/* ━━━━ SIGNAL TAGS ━━━━ */
.stag {
  display: inline-block; font-size: 12px; padding: 5px 12px;
  border-radius: 20px; font-weight: 600; margin: 3px;
}
.stag.b { background: #d1fae5; color: #065f46; border: 1px solid #6ee7b7; }
.stag.s { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }

/* ━━━━ SCORE RING ━━━━ */
.ring {
  width: 68px; height: 68px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  border: 3px solid; font-size: 22px; font-weight: 700;
  font-family: 'JetBrains Mono', monospace; flex-shrink: 0;
}
.ring.h { color: #059669; border-color: #34d399; background: #d1fae5; }
.ring.m { color: #b45309; border-color: #fbbf24; background: #fef3c7; }
.ring.l { color: #dc2626; border-color: #f87171; background: #fee2e2; }

/* ━━━━ CHIP SIGNALS ━━━━ */
.chip-buy   { display:inline-block;background:#d1fae5;color:#065f46;border:1.5px solid #6ee7b7;border-radius:20px;padding:4px 14px;font-weight:700;font-size:13px; }
.chip-sell  { display:inline-block;background:#fee2e2;color:#991b1b;border:1.5px solid #fca5a5;border-radius:20px;padding:4px 14px;font-weight:700;font-size:13px; }
.chip-watch { display:inline-block;background:#fef3c7;color:#92400e;border:1.5px solid #fde68a;border-radius:20px;padding:4px 14px;font-weight:700;font-size:13px; }
.chip-hold  { display:inline-block;background:#e0e7ff;color:#4338ca;border:1.5px solid #c7d2fe;border-radius:20px;padding:4px 14px;font-weight:700;font-size:13px; }

/* ━━━━ PROGRESS BAR ━━━━ */
div[data-testid="stProgressBar"] > div {
  background: #e0e7ff !important;
  border-radius: 99px !important;
}
div[data-testid="stProgressBar"] > div > div {
  background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
  border-radius: 99px !important;
}
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
    """คำนวณ indicators ครบทุกตัว จาก OHLCV dataframe"""
    if df is None or len(df) < 30:
        return {}
    try:
        # Flatten MultiIndex ถ้ามี แล้ว force float
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() if isinstance(col, tuple) else str(col).lower()
                          for col in df.columns]
        # squeeze ถ้า column เป็น DataFrame แทน Series
        def to_series(col):
            s = df[col]
            if isinstance(s, pd.DataFrame):
                s = s.iloc[:, 0]
            return s.astype(float).reset_index(drop=True)

        c  = to_series("close")
        h  = to_series("high")
        lo = to_series("low")
        v  = to_series("volume")
        n  = len(c)
        p  = float(c.iloc[-1])

        def sma(s, per):
            try: return float(s.rolling(per).mean().iloc[-1])
            except: return p
        def ema(s, per):
            try: return float(s.ewm(span=per, adjust=False).mean().iloc[-1])
            except: return float(s.iloc[-1]) if len(s)>0 else p
        def safe(val, default=0.0):
            try:
                v2 = float(val)
                return v2 if v2 == v2 else default  # NaN check
            except: return default

        # ── Moving Averages ──────────────────────────────────────
        sma5   = sma(c, min(5,n));   sma10 = sma(c, min(10,n))
        sma20  = sma(c, min(20,n));  sma50 = sma(c, min(50,n))
        sma200 = sma(c, min(200,n))
        ema9   = ema(c, 9);   ema12 = ema(c, 12)
        ema20_ = ema(c, 20);  ema26 = ema(c, 26)
        ema50_ = ema(c, 50);  ema200_= ema(c, 200)

        # ── MACD ────────────────────────────────────────────────
        macd_line   = ema12 - ema26
        _ms = pd.Series([
            ema(c.iloc[max(0,i-35):i+1], 12) - ema(c.iloc[max(0,i-35):i+1], 26)
            for i in range(n)
        ])
        macd_signal = ema(_ms, 9)
        macd_hist   = macd_line - macd_signal

        # ── RSI ─────────────────────────────────────────────────
        d    = c.diff()
        gain = d.clip(lower=0).rolling(14).mean()
        loss = (-d.clip(upper=0)).rolling(14).mean()
        rsi_s= 100 - 100 / (1 + gain / (loss + 1e-9))
        rsi  = safe(rsi_s.iloc[-1], 50)
        rsi6 = safe(
            100 - 100 / (1 + d.clip(lower=0).rolling(6).mean().iloc[-1] /
                         ((-d.clip(upper=0)).rolling(6).mean().iloc[-1] + 1e-9)), 50)

        # ── Bollinger Bands ──────────────────────────────────────
        bb_mid = sma(c, 20)
        bb_std = safe(c.rolling(20).std().iloc[-1], 0)
        bb_up  = bb_mid + 2 * bb_std
        bb_dn  = bb_mid - 2 * bb_std
        bb_w   = (bb_up - bb_dn) / (bb_mid + 1e-9)
        bb_pct = (p - bb_dn) / (bb_up - bb_dn + 1e-9)

        # ── Stochastic ───────────────────────────────────────────
        hh14  = safe(h.rolling(14).max().iloc[-1], p)
        ll14  = safe(lo.rolling(14).min().iloc[-1], p)
        stochK= (p - ll14) / (hh14 - ll14 + 1e-9) * 100
        _stoch_series = pd.Series([
            (float(c.iloc[i]) - safe(lo.rolling(14).min().iloc[i], float(c.iloc[i]))) /
            (safe(h.rolling(14).max().iloc[i], float(c.iloc[i])) -
             safe(lo.rolling(14).min().iloc[i], float(c.iloc[i])) + 1e-9) * 100
            for i in range(n)
        ])
        stochD = safe(_stoch_series.rolling(3).mean().iloc[-1], stochK)

        # ── ATR ─────────────────────────────────────────────────
        tr = pd.concat([
            h - lo,
            (h - c.shift()).abs(),
            (lo - c.shift()).abs()
        ], axis=1).max(axis=1)
        atr  = safe(tr.rolling(14).mean().iloc[-1], p * 0.02)
        atr7 = safe(tr.rolling(7).mean().iloc[-1],  p * 0.015)

        # ── ADX ─────────────────────────────────────────────────
        dmp  = (h - h.shift()).clip(lower=0)
        dmm  = (lo.shift() - lo).clip(lower=0)
        dmp2 = dmp.where(dmp > dmm, 0)
        dmm2 = dmm.where(dmm > dmp, 0)
        a14  = tr.rolling(14).mean()
        dip  = safe((dmp2.rolling(14).mean() / (a14 + 1e-9) * 100).iloc[-1])
        dim  = safe((dmm2.rolling(14).mean() / (a14 + 1e-9) * 100).iloc[-1])
        adx  = safe(abs(dip - dim) / (dip + dim + 1e-9) * 100)

        # ── CCI ─────────────────────────────────────────────────
        tp_s = (h + lo + c) / 3
        cci  = safe(
            (float(tp_s.iloc[-1]) - float(tp_s.rolling(20).mean().iloc[-1])) /
            (0.015 * float(tp_s.rolling(20).std().iloc[-1]) + 1e-9))

        # ── Williams %R ──────────────────────────────────────────
        willr = safe((hh14 - p) / (hh14 - ll14 + 1e-9) * -100)

        # ── MFI ─────────────────────────────────────────────────
        tp_mfi = (h + lo + c) / 3
        mf     = tp_mfi * v
        pos_mf = mf.where(tp_mfi > tp_mfi.shift(), 0).rolling(14).sum()
        neg_mf = mf.where(tp_mfi <= tp_mfi.shift(), 0).rolling(14).sum()
        mfi    = safe(100 - 100 / (1 + float(pos_mf.iloc[-1]) /
                                   (float(neg_mf.iloc[-1]) + 1e-9)))

        # ── OBV ─────────────────────────────────────────────────
        obv_cur = 0.0
        obv_vals= [0.0]
        for i in range(1, n):
            ci, ci_prev = float(c.iloc[i]), float(c.iloc[i-1])
            vi = float(v.iloc[i])
            obv_cur += vi if ci > ci_prev else (-vi if ci < ci_prev else 0)
            obv_vals.append(obv_cur)
        obv_s    = pd.Series(obv_vals)
        obv      = obv_vals[-1]
        obv_ema  = ema(obv_s, 20)
        obv_trend= "up" if obv > obv_ema else "down"

        # ── ROC ─────────────────────────────────────────────────
        roc10 = safe((p / float(c.iloc[-11]) - 1) * 100) if n > 10 else 0
        roc20 = safe((p / float(c.iloc[-21]) - 1) * 100) if n > 20 else 0

        # ── VWAP ────────────────────────────────────────────────
        vwap = safe(float((tp_s * v).rolling(20).sum().iloc[-1]) /
                    (float(v.rolling(20).sum().iloc[-1]) + 1e-9))

        # ── Volume ──────────────────────────────────────────────
        vol_avg20 = safe(float(v.rolling(20).mean().iloc[-1]), 1)
        vol_avg5  = safe(float(v.rolling(5).mean().iloc[-1]),  1)
        vol_r     = safe(float(v.iloc[-1]) / (vol_avg20 + 1))
        vol_r5    = safe(vol_avg5 / (vol_avg20 + 1))

        # ── 52W ─────────────────────────────────────────────────
        w    = min(252, n)
        h52  = safe(float(h.rolling(w).max().iloc[-1]), p)
        l52  = safe(float(lo.rolling(w).min().iloc[-1]), p)
        pct_from_h52 = (p / h52 - 1) * 100 if h52 > 0 else 0
        pct_from_l52 = (p / l52 - 1) * 100 if l52 > 0 else 0

        # ── Pivot / CPR ──────────────────────────────────────────
        ph  = safe(float(h.iloc[-2]),  p)
        pl2 = safe(float(lo.iloc[-2]), p)
        pc2 = safe(float(c.iloc[-2]),  p)
        pvt = (ph + pl2 + pc2) / 3
        rng = ph - pl2
        r1  = 2*pvt - pl2;  r2 = pvt + rng;  r3 = ph + 2*(pvt - pl2)
        s1  = 2*pvt - ph;   s2 = pvt - rng;  s3 = pl2 - 2*(ph - pvt)
        cpr_top = (ph + pl2) / 2
        cpr_bot = pvt
        cpr_w   = abs(cpr_top - cpr_bot)

        # ── Change ──────────────────────────────────────────────
        chg   = safe((p / float(c.iloc[-2])  - 1) * 100) if n > 1  else 0
        chg5  = safe((p / float(c.iloc[-6])  - 1) * 100) if n > 5  else 0
        chg20 = safe((p / float(c.iloc[-21]) - 1) * 100) if n > 20 else 0

        # ── Trend ────────────────────────────────────────────────
        above_ema9   = p > ema9
        above_ema20  = p > ema20_
        above_ema50  = p > ema50_
        above_ema200 = p > ema200_
        golden_cross = ema50_ > ema200_
        trend_score  = sum([above_ema9, above_ema20, above_ema50, above_ema200])

        return dict(
            price=p, chg=chg, chg5=chg5, chg20=chg20,
            sma5=sma5, sma10=sma10, sma20=sma20, sma50=sma50, sma200=sma200,
            ema9=ema9, ema20=ema20_, ema50=ema50_, ema200=ema200_,
            macd=macd_hist, macd_line=macd_line, macd_signal=macd_signal,
            rsi=rsi, rsi6=rsi6,
            bb_pct=bb_pct, bb_up=bb_up, bb_dn=bb_dn, bb_mid=bb_mid, bb_w=bb_w,
            stoch=stochK, stochD=stochD,
            atr=atr, atr7=atr7,
            adx=adx, dip=dip, dim=dim,
            cci=cci, willr=willr, mfi=mfi, roc10=roc10, roc20=roc20,
            vwap=vwap, vol_r=vol_r, vol_r5=vol_r5, obv=obv, obv_trend=obv_trend,
            h52=h52, l52=l52, pct_from_h52=pct_from_h52, pct_from_l52=pct_from_l52,
            pivot=pvt, r1=r1, r2=r2, r3=r3, s1=s1, s2=s2, s3=s3,
            cpr_top=cpr_top, cpr_bot=cpr_bot, cpr_w=cpr_w,
            golden_cross=golden_cross, trend_score=trend_score,
            above_ema9=above_ema9, above_ema20=above_ema20,
            above_ema50=above_ema50, above_ema200=above_ema200,
        )
    except Exception as e:
        return {}


def score(I, os=35, ob=65):
    """คำนวณคะแนน 0-100 จาก indicators ครบทุกตัว"""
    if not I: return {}
    sc = 50; bs = []; ss = []; ns = []
    p  = I.get("price", 0)
    if p <= 0: return {}

    # ── RSI (max ±10) ────────────────────────────────────────
    r = I.get("rsi", 50)
    if   r < os:      sc += 10; bs.append(f"RSI {r:.1f} Oversold — โอกาส Bounce")
    elif r < 40:      sc += 5;  bs.append(f"RSI {r:.1f} ค่อนข้าง Oversold")
    elif r > ob:      sc -= 10; ss.append(f"RSI {r:.1f} Overbought — ระวัง Pullback")
    elif r > 60:      sc -= 4;  ss.append(f"RSI {r:.1f} ค่อนข้าง Overbought")
    else:             ns.append(f"RSI {r:.1f} Neutral")

    # ── RSI6 ─────────────────────────────────────────────────
    r6 = I.get("rsi6", 50)
    if   r6 < 20: sc += 4; bs.append(f"RSI6 {r6:.1f} Extreme Oversold")
    elif r6 > 80: sc -= 4; ss.append(f"RSI6 {r6:.1f} Extreme Overbought")

    # ── MACD (max ±9) ────────────────────────────────────────
    mh = I.get("macd", 0)
    ml = I.get("macd_line", 0)
    ms = I.get("macd_signal", 0)
    if mh > 0 and ml > 0:  sc += 9; bs.append("MACD บวก + อยู่เหนือ Signal")
    elif mh > 0:            sc += 5; bs.append("MACD Histogram บวก (momentum เริ่มกลับ)")
    elif mh < 0 and ml < 0: sc -= 9; ss.append("MACD ลบ + อยู่ต่ำกว่า Signal")
    elif mh < 0:            sc -= 5; ss.append("MACD Histogram ลบ (momentum อ่อน)")

    # ── Stochastic (max ±6) ──────────────────────────────────
    sk = I.get("stoch", 50); sd = I.get("stochD", 50)
    if   sk < 20 and sk > sd: sc += 6; bs.append(f"Stoch %K {sk:.0f} Oversold + %K ตัด %D ขึ้น")
    elif sk < 20:             sc += 4; bs.append(f"Stoch %K {sk:.0f} Oversold")
    elif sk > 80 and sk < sd: sc -= 6; ss.append(f"Stoch %K {sk:.0f} Overbought + %K ตัด %D ลง")
    elif sk > 80:             sc -= 4; ss.append(f"Stoch %K {sk:.0f} Overbought")

    # ── Bollinger Bands (max ±8) ─────────────────────────────
    bp = I.get("bb_pct", 0.5); bw = I.get("bb_w", 0.1)
    bup = I.get("bb_up", p)
    if   bp < 0.05: sc += 8; bs.append("ราคาต่ำกว่า BB Lower — Oversold รุนแรง")
    elif bp < 0.20: sc += 5; bs.append(f"BB%B {bp:.2f} ใกล้ Lower Band")
    elif bp > 0.95: sc -= 7; ss.append("ราคาสูงกว่า BB Upper — Overbought รุนแรง")
    elif bp > 0.80: sc -= 4; ss.append(f"BB%B {bp:.2f} ใกล้ Upper Band")
    if p > bup:     sc += 3; bs.append("Breakout เหนือ BB Upper (แรง)")
    if bw < 0.05:   ns.append(f"BB Squeeze (width {bw:.3f}) — เตรียม Breakout")

    # ── ADX / DI (max ±7) ───────────────────────────────────
    ax  = I.get("adx", 0); dp = I.get("dip", 25); dm = I.get("dim", 25)
    if ax > 30:
        if dp > dm:   sc += 7; bs.append(f"ADX {ax:.0f} Trend แข็งมาก DI+>{dm:.0f}")
        elif dm > dp: sc -= 7; ss.append(f"ADX {ax:.0f} Downtrend แข็ง DI->{dp:.0f}")
    elif ax > 20:
        if dp > dm:   sc += 4; bs.append(f"ADX {ax:.0f} Uptrend เริ่มแข็ง")
        elif dm > dp: sc -= 4; ss.append(f"ADX {ax:.0f} Downtrend เริ่มแข็ง")
    else:             ns.append(f"ADX {ax:.0f} Sideways / Weak Trend")

    # ── EMA Alignment (max ±8) ──────────────────────────────
    ts = I.get("trend_score", 2)  # 0-4
    gc = I.get("golden_cross", False)
    if   ts == 4: sc += 8; bs.append("ราคาเหนือ EMA ทุกเส้น (9/20/50/200) — Full Bull")
    elif ts == 3: sc += 5; bs.append(f"ราคาเหนือ EMA {ts}/4 เส้น")
    elif ts == 1: sc -= 5; ss.append(f"ราคาต่ำกว่า EMA เกือบทุกเส้น ({ts}/4)")
    elif ts == 0: sc -= 8; ss.append("ราคาต่ำกว่า EMA ทุกเส้น — Full Bear")
    if gc:        sc += 3; bs.append("EMA50 > EMA200 (Golden Cross)")
    elif not gc and I.get("ema50",0) > 0:
                  sc -= 3; ss.append("EMA50 < EMA200 (Death Cross)")

    # ── SMA20/50 Cross (max ±5) ──────────────────────────────
    s20 = I.get("sma20", p); s50 = I.get("sma50", p); s200 = I.get("sma200", p)
    if p > s20 > s50:    sc += 5; bs.append("ราคา > SMA20 > SMA50 Uptrend")
    elif p < s20 < s50:  sc -= 5; ss.append("ราคา < SMA20 < SMA50 Downtrend")
    if s200 > 0:
        diff200 = (p / s200 - 1) * 100
        if p > s200:     sc += 3; bs.append(f"เหนือ SMA200 +{diff200:.1f}%")
        else:            sc -= 3; ss.append(f"ต่ำกว่า SMA200 {diff200:.1f}%")

    # ── CCI (max ±5) ─────────────────────────────────────────
    cci = I.get("cci", 0)
    if   cci < -100: sc += 5; bs.append(f"CCI {cci:.0f} Oversold")
    elif cci < -200: sc += 7; bs.append(f"CCI {cci:.0f} Extreme Oversold")
    elif cci > 100:  sc -= 4; ss.append(f"CCI {cci:.0f} Overbought")
    elif cci > 200:  sc -= 6; ss.append(f"CCI {cci:.0f} Extreme Overbought")

    # ── Williams %R (max ±4) ────────────────────────────────
    wr = I.get("willr", -50)
    if   wr < -80: sc += 4; bs.append(f"Williams%R {wr:.0f} Oversold")
    elif wr > -20: sc -= 4; ss.append(f"Williams%R {wr:.0f} Overbought")

    # ── MFI (max ±5) ─────────────────────────────────────────
    mfi = I.get("mfi", 50)
    if   mfi < 20: sc += 5; bs.append(f"MFI {mfi:.0f} — เงินไหลเข้า Oversold")
    elif mfi < 30: sc += 3; bs.append(f"MFI {mfi:.0f} — ค่อนข้าง Oversold")
    elif mfi > 80: sc -= 5; ss.append(f"MFI {mfi:.0f} — เงินไหลออก Overbought")
    elif mfi > 70: sc -= 3; ss.append(f"MFI {mfi:.0f} — ค่อนข้าง Overbought")

    # ── ROC (max ±4) ────────────────────────────────────────
    roc = I.get("roc10", 0)
    if   roc < -10: sc += 4; bs.append(f"ROC10 {roc:.1f}% ลงมามาก โอกาส Bounce")
    elif roc > 15:  sc -= 3; ss.append(f"ROC10 {roc:.1f}% ขึ้นมาเร็ว ระวัง")

    # ── VWAP (max ±4) ────────────────────────────────────────
    vw = I.get("vwap", p)
    pct_vwap = (p / vw - 1) * 100 if vw > 0 else 0
    if   p > vw: sc += 4; bs.append(f"ราคา > VWAP +{pct_vwap:.1f}%")
    else:        sc -= 4; ss.append(f"ราคา < VWAP {pct_vwap:.1f}%")

    # ── OBV (max ±4) ────────────────────────────────────────
    if I.get("obv_trend") == "up":   sc += 4; bs.append("OBV > EMA20 — Volume ยืนยัน Uptrend")
    else:                            sc -= 4; ss.append("OBV < EMA20 — Volume ไม่ยืนยัน Trend")

    # ── Volume Ratio (max ±3) ───────────────────────────────
    vr = I.get("vol_r", 1)
    if   vr > 2.0: sc += 3; bs.append(f"Volume {vr:.1f}x สูงผิดปกติ — มีแรงซื้อ/ขาย")
    elif vr > 1.5: sc += 2; bs.append(f"Volume {vr:.1f}x สูงกว่าค่าเฉลี่ย")
    elif vr < 0.5: ns.append(f"Volume {vr:.1f}x ต่ำ — ระวังสัญญาณหลอก")

    # ── 52W Position (max ±3) ───────────────────────────────
    ph52 = I.get("pct_from_h52", 0); pl52 = I.get("pct_from_l52", 0)
    if   ph52 < -30: sc += 3; bs.append(f"ห่างจาก 52W High {ph52:.0f}% — มี Upside เยอะ")
    elif ph52 > -5:  sc -= 2; ss.append(f"ใกล้ 52W High {ph52:.0f}% — ระวัง Resistance")
    if   pl52 < 10:  sc += 2; bs.append(f"ใกล้ 52W Low +{pl52:.0f}% — โซน Support แนวรับ")

    sc  = int(max(0, min(100, sc)))
    sig = "buy" if sc >= 65 else "sell" if sc <= 35 else "watch" if sc >= 55 else "hold"
    at  = I.get("atr", p * 0.02) or p * 0.02
    en  = round(p * 0.985, 2)
    t1  = round(p + at * 2, 2)
    t2  = round(p + at * 3.5, 2)
    sl  = round(p - at * 1.5, 2)
    up  = round(((t1 / p) - 1) * 100, 1) if p > 0 else 0
    dn  = round(((p / sl) - 1) * 100, 1) if sl > 0 else 1
    rr  = round(up / dn, 2) if dn > 0 else 0
    return dict(sc=sc, sig=sig, bs=bs, ss=ss, ns=ns,
                entry=en, t1=t1, t2=t2, sl=sl, up=up, dn=dn, rr=rr)


# ── Scan parameter tips ──────────────────────────────────────
SCAN_TIPS = {
    "ตลาดขาขึ้น (Bull Market)": {
        "p_rsi_os": 40, "p_rsi_ob": 75, "p_min_sc": 60, "p_min_rr": 1.5,
        "คำอธิบาย": "ขยาย RSI Oversold เป็น 40 เพื่อเจอหุ้นที่ pullback ในตลาดขาขึ้น"
    },
    "ตลาดขาลง (Bear Market)": {
        "p_rsi_os": 25, "p_rsi_ob": 60, "p_min_sc": 70, "p_min_rr": 2.0,
        "คำอธิบาย": "เข้มงวดขึ้น — รอสัญญาณชัดมาก R/R ดีมาก จึงค่อยซื้อ"
    },
    "ตลาด Sideways": {
        "p_rsi_os": 30, "p_rsi_ob": 70, "p_min_sc": 55, "p_min_rr": 1.2,
        "คำอธิบาย": "ค่ากลาง — เจอหุ้นที่ swing trade ได้ในกรอบ"
    },
    "หา Breakout": {
        "p_rsi_os": 50, "p_rsi_ob": 80, "p_min_sc": 65, "p_min_rr": 2.0,
        "คำอธิบาย": "RSI สูง + Score สูง = หุ้น Breakout พร้อมวิ่ง"
    },
    "หา Oversold Bounce": {
        "p_rsi_os": 35, "p_rsi_ob": 65, "p_min_sc": 50, "p_min_rr": 1.5,
        "คำอธิบาย": "ค่า Default — หุ้นที่ลงมามากและกำลัง Bounce"
    },
}


def st_candles(sym, mkt_api, limit=365):
    """ดึง OHLCV รายวัน — แสดง debug info ถ้าดึงไม่ได้"""
    from datetime import datetime, timedelta
    end_dt   = datetime.now().strftime("%Y-%m-%d")
    start_dt = (datetime.now() - timedelta(days=limit)).strftime("%Y-%m-%d")
    errors   = []
    data     = None

    # ลอง get_candlestick ด้วย parameter หลายแบบ
    candlestick_attempts = [
        lambda: mkt_api.get_candlestick(sym, interval="1D", limit=limit),
        lambda: mkt_api.get_candlestick(sym, interval="1d", limit=limit),
        lambda: mkt_api.get_candlestick(sym, "1D", limit),
        lambda: mkt_api.get_candlestick(sym, "1d", limit),
        lambda: mkt_api.get_candlestick(sym),
    ]
    if hasattr(mkt_api, 'get_candlestick'):
        for i, call in enumerate(candlestick_attempts):
            try:
                data = call()
                if data:
                    break
                errors.append(f"get_candlestick[{i}]: returned empty")
            except Exception as e:
                err_str = str(e)
                errors.append(f"get_candlestick[{i}]: {err_str}")
                # ถ้า token หมดอายุ หยุดเลย
                if any(x in err_str.lower() for x in
                       ['token', 'expired', 'unauthorized', '401', 'invalid']):
                    raise RuntimeError(
                        f"Token หมดอายุหรือไม่ถูกต้อง\n"
                        f"กรุณากด 'ออกจากระบบ' แล้ว Login ใหม่\n"
                        f"(Error: {err_str})"
                    )
    else:
        errors.append("get_candlestick: not found")

    # ลอง methods อื่น
    other_attempts = [
        ('get_price_chart_by_period',  lambda: mkt_api.get_price_chart_by_period(sym, "1D")),
        ('get_price_chart_by_period',  lambda: mkt_api.get_price_chart_by_period(sym, "1d")),
        ('get_quotation_range',        lambda: mkt_api.get_quotation_range(sym, start_dt, end_dt)),
        ('get_historical_price',       lambda: mkt_api.get_historical_price(sym, start_dt, end_dt)),
        ('get_price',                  lambda: mkt_api.get_price(sym)),
    ]
    if data is None:
        for method_name, call in other_attempts:
            if hasattr(mkt_api, method_name):
                try:
                    data = call()
                    if data:
                        break
                    errors.append(f"{method_name}: returned empty")
                except Exception as e:
                    errors.append(f"{method_name}: {e}")
            else:
                errors.append(f"{method_name}: not found")

    if not data:
        all_methods = [m for m in dir(mkt_api) if not m.startswith('_')]
        err_str = '; '.join(errors)
        # ตรวจว่า token หมดอายุไหม
        if 'access token' in err_str.lower() or 'expired' in err_str.lower() or 'invalid' in err_str.lower():
            raise RuntimeError(
                f"Token หมดอายุ — กรุณากด 'ออกจากระบบ' แล้ว Login ใหม่\n"
                f"(Error: {err_str[:100]})"
            )
        raise RuntimeError(
            f"ไม่สามารถดึงข้อมูล {sym} ได้\n"
            f"Methods ที่มี: {all_methods}\n"
            f"Errors: {err_str}"
        )

    df = pd.DataFrame(data)

    # Flatten MultiIndex columns ถ้ามี (เช่น ('close','ADVANC') → 'close')
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower()
                      for c in df.columns]
    else:
        df.columns = [str(c).lower() for c in df.columns]

    # Rename columns ให้เป็น OHLCV มาตรฐาน
    rename = {}
    for col in df.columns:
        cl = col.lower().strip()
        if any(x in cl for x in ["close", "last", "price"]):
            if "close" not in rename.values(): rename[col] = "close"
        elif cl in ["open", "o"]:   rename[col] = "open"
        elif cl in ["high", "h"]:   rename[col] = "high"
        elif cl in ["low",  "l"]:   rename[col] = "low"
        elif any(x in cl for x in ["vol", "volume"]) or cl == "v":
            rename[col] = "volume"
    df = df.rename(columns=rename)
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            df[col] = 0
    df = df[["open","high","low","close","volume"]]
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=["close"])
    df = df.reset_index(drop=True)
    return df


def st_quote(sym, rt_api):
    """ดึงราคา real-time รองรับทุก version ของ settrade-v2"""
    if rt_api is None:
        return {}
    try:
        # Version ใหม่: RealtimeDataConnection
        if hasattr(rt_api, 'get_quote_symbol'):
            return rt_api.get_quote_symbol(sym) or {}
        elif hasattr(rt_api, 'get_quote'):
            return rt_api.get_quote(sym) or {}
        # RealtimeDataConnection อาจต้องเรียกแบบนี้
        elif hasattr(rt_api, 'get_security_info'):
            return rt_api.get_security_info(sym) or {}
        elif callable(rt_api):
            # บาง version เรียก rt_api(sym) โดยตรง
            return rt_api(sym) or {}
        return {}
    except Exception:
        return {}

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
    from datetime import datetime, timedelta
    mkt_th  = {"SET":"ตลาดหุ้นไทย SET","US":"ตลาด NASDAQ/NYSE","CN":"ตลาด NYSE CN ADR"}
    sig_map = {"buy":"ซื้อ","sell":"ขาย","watch":"เฝ้าระวัง","hold":"ถือ"}
    today     = datetime.now().strftime("%d %B %Y")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%d %B %Y")
    month_name= datetime.now().strftime("%B %Y")
    p = I.get("price", 0)

    ind_block = f"""
📊 INDICATORS ณ วันที่ {today}

[ราคาและผลตอบแทน]
  ราคาล่าสุด  = {cur}{fmt(p)}
  เปลี่ยน 1D  = {I.get('chg',0):+.2f}%   |  5D = {I.get('chg5',0):+.2f}%   |  20D = {I.get('chg20',0):+.2f}%

[Moving Averages]
  SMA5={cur}{fmt(I.get('sma5',0))}  SMA10={cur}{fmt(I.get('sma10',0))}  SMA20={cur}{fmt(I.get('sma20',0))}
  SMA50={cur}{fmt(I.get('sma50',0))}  SMA200={cur}{fmt(I.get('sma200',0))}
  EMA9={cur}{fmt(I.get('ema9',0))}  EMA20={cur}{fmt(I.get('ema20',0))}  EMA50={cur}{fmt(I.get('ema50',0))}  EMA200={cur}{fmt(I.get('ema200',0))}
  Golden Cross: {"✅ ใช่ (EMA50>EMA200)" if I.get('golden_cross') else "❌ ไม่ใช่ (Death Cross)"}
  Trend Score: {I.get('trend_score',0)}/4 (ราคาเหนือ EMA กี่เส้น)

[Momentum]
  RSI(14)  = {I.get('rsi',50):.1f}  |  RSI(6)  = {I.get('rsi6',50):.1f}
  MACD Line= {I.get('macd_line',0):.4f}  |  Signal= {I.get('macd_signal',0):.4f}  |  Hist= {I.get('macd',0):.4f}
  Stoch %K = {I.get('stoch',50):.1f}  |  %D= {I.get('stochD',50):.1f}
  CCI(20)  = {I.get('cci',0):.1f}
  Williams%R= {I.get('willr',-50):.1f}
  ROC(10)  = {I.get('roc10',0):.2f}%  |  ROC(20)= {I.get('roc20',0):.2f}%

[Volatility]
  Bollinger %B   = {I.get('bb_pct',0.5):.3f}
  BB Upper={cur}{fmt(I.get('bb_up',0))}  Mid={cur}{fmt(I.get('bb_mid',0))}  Lower={cur}{fmt(I.get('bb_dn',0))}
  BB Width (Bandwidth) = {I.get('bb_w',0):.4f}  {"⚡ Squeeze!" if I.get('bb_w',1)<0.05 else ""}
  ATR(14) = {cur}{fmt(I.get('atr',0))}  |  ATR(7) = {cur}{fmt(I.get('atr7',0))}

[Volume & Money Flow]
  Volume Ratio  = {I.get('vol_r',1):.2f}x  |  5D/20D Avg = {I.get('vol_r5',1):.2f}x
  VWAP          = {cur}{fmt(I.get('vwap',0))}  (ราคา {"เหนือ" if p>I.get('vwap',p) else "ต่ำกว่า"} VWAP)
  MFI(14)       = {I.get('mfi',50):.1f}
  OBV Trend     = {I.get('obv_trend','?').upper()}  (OBV {">" if I.get('obv_trend')=='up' else "<"} EMA20)

[Trend Strength]
  ADX(14) = {I.get('adx',0):.1f}  |  DI+= {I.get('dip',0):.1f}  |  DI-= {I.get('dim',0):.1f}
  {"Uptrend แข็ง" if I.get('adx',0)>25 and I.get('dip',0)>I.get('dim',0) else "Downtrend แข็ง" if I.get('adx',0)>25 else "Sideways/Weak"}

[Price Position]
  52W High = {cur}{fmt(I.get('h52',0))}  (ห่าง {I.get('pct_from_h52',0):.1f}%)
  52W Low  = {cur}{fmt(I.get('l52',0))}  (ห่าง +{I.get('pct_from_l52',0):.1f}%)

[Pivot Points & CPR]
  R3={cur}{fmt(I.get('r3',0))}  R2={cur}{fmt(I.get('r2',0))}  R1={cur}{fmt(I.get('r1',0))}
  Pivot={cur}{fmt(I.get('pivot',0))}
  S1={cur}{fmt(I.get('s1',0))}  S2={cur}{fmt(I.get('s2',0))}  S3={cur}{fmt(I.get('s3',0))}
  CPR Top={cur}{fmt(I.get('cpr_top',0))}  Bot={cur}{fmt(I.get('cpr_bot',0))}  Width={cur}{fmt(I.get('cpr_w',0))}

[AI Score Summary]
  คะแนนรวม = {S.get('sc',50)}/100  |  สัญญาณ = {sig_map.get(S.get('sig','hold'),'ถือ')}
  จุดซื้อแนะนำ={cur}{S.get('entry',0)}  เป้า1={cur}{S.get('t1',0)}  เป้า2={cur}{S.get('t2',0)}  SL={cur}{S.get('sl',0)}  R/R=1:{S.get('rr',0)}
  Bullish signals: {len(S.get('bs',[]))} | Bearish signals: {len(S.get('ss',[]))}
"""

    return (
        f"คุณคือนักวิเคราะห์หุ้นมืออาชีพ วันนี้คือ {today}\n\n"

        f"# วิเคราะห์หุ้น {sym} ({mkt_th.get(mkt,mkt)})\n\n"

        f"## ขั้นตอนที่ 1 — ค้นข่าว 1 เดือนล่าสุด (ทำก่อน)\n"
        f"ค้นหาข่าวของ {sym} ที่เกิดขึ้นใน {month_ago} ถึง {today} จากแหล่งต่างๆ:\n"
        f'- ค้น: "{sym} ข่าว {month_name}"\n'
        f'- ค้น: "{sym} stock news {month_name}"\n'
        f'- ค้น: "{sym} ผลประกอบการ earnings {month_name}"\n'
        f"สรุปแต่ละข่าวในรูปแบบ:\n"
        f"📅 [วันที่] [หัวข้อ] — ผลกระทบ: บวก/ลบ/กลาง — [อธิบาย 1 ประโยค]\n\n"

        f"## ขั้นตอนที่ 2 — วิเคราะห์ Sentiment ข่าว\n"
        f"สรุปทิศทางข่าวโดยรวม: บวก/ลบ/ผสม และระดับความรุนแรง\n\n"

        f"## ขั้นตอนที่ 3 — วิเคราะห์ Technical Indicators\n"
        f"ข้อมูล indicators ทั้งหมด:\n{ind_block}\n"
        f"วิเคราะห์แต่ละกลุ่ม indicators อย่างละเอียด:\n"
        f"- Moving Averages บอกอะไร? trend ชัดแค่ไหน?\n"
        f"- Momentum (RSI/MACD/Stoch/CCI/Williams%R) บอกอะไร? สอดคล้องกันไหม?\n"
        f"- Volatility (BB/ATR) บอกอะไร? มี Squeeze ไหม?\n"
        f"- Volume & Money Flow (MFI/OBV/Vol Ratio) ยืนยัน trend ไหม?\n"
        f"- Pivot/Support/Resistance ที่สำคัญอยู่ที่ไหน?\n\n"

        f"## ขั้นตอนที่ 4 — Confluence Analysis\n"
        f"ข่าวและ indicators ชี้ไปทางเดียวกันไหม? หรือขัดแย้ง? อธิบาย\n\n"

        f"## ขั้นตอนที่ 5 — คำแนะนำ\n"
        f"ระบุชัดว่า ซื้อ/ขาย/ถือ/รอ พร้อมเหตุผล:\n"
        f"  จุดซื้อ = {cur}{S.get('entry',0)} | เป้า1 = {cur}{S.get('t1',0)} | เป้า2 = {cur}{S.get('t2',0)} | SL = {cur}{S.get('sl',0)} | R/R = 1:{S.get('rr',0)}\n\n"

        f"## ขั้นตอนที่ 6 — ความเสี่ยง\n"
        f"ระบุ 2-3 ความเสี่ยงสำคัญ\n\n"
        f"ตอบภาษาไทย ละเอียดแต่กระชับ"
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
            "maxOutputTokens": 3000,
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
        json={"model":"claude-sonnet-4-20250514","max_tokens":3000,
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



# ── Settings moved to inline tab (mobile-friendly) ──────────
# All sidebar config is now inside the ⚙️ tab


# ── Main header ───────────────────────────────────────────────
st.markdown("""
<div style="padding:20px 0 12px;text-align:center">
  <div style="font-size:30px;font-weight:700;background:linear-gradient(135deg,#6366f1,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">
    📈 Stock Pro
  </div>
  <div style="font-size:13px;color:#818cf8;margin-top:6px;font-weight:500;letter-spacing:.5px">
    SETTRADE REAL-TIME · SET50 · US TECH · CN TECH · AI POWERED
  </div>
</div>
""", unsafe_allow_html=True)

# ── SETUP CARD (แสดงในหน้าหลัก ไม่ต้องง้อ sidebar) ──────────
# ══════════════════════════════════════════════════════════════
# SETTRADE LOGIN GATE — แสดงก่อนเข้าใช้งาน
# ══════════════════════════════════════════════════════════════
if not st.session_state.get("st_ok"):
    if not SETTRADE_OK:
        # ไม่มี settrade — แสดง warning แล้วข้ามไปให้ใช้ US/CN
        st.warning("⚠️ settrade-v2 ไม่ได้ติดตั้ง — SET50 ใช้ไม่ได้\n\n"
                   "ติดตั้งด้วย: `pip install settrade-v2` แล้ว restart\n\n"
                   "หรือใช้ **US Tech / CN Tech** ซึ่งไม่ต้องการ Settrade")
    else:
        st.markdown("""
        <div style="text-align:center;padding:10px 0 20px">
          <div style="font-size:16px;color:#818cf8;font-weight:500">
            🔐 กรอก Settrade API Credential เพื่อเริ่มใช้งาน
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;padding:10px 0 20px">
          <div style="font-size:16px;color:#818cf8;font-weight:500">
            🔐 กรอก Settrade API Credential เพื่อเริ่มใช้งาน
          </div>
        </div>
        """, unsafe_allow_html=True)
    
        with st.form("login_gate"):
            lg1, lg2 = st.columns(2)
            with lg1:
                lg_id    = st.text_input("APP_ID",     placeholder="กรอก APP_ID จาก developer.settrade.com")
                lg_sec   = st.text_input("APP_SECRET", placeholder="กรอก APP_SECRET", type="password")
                lg_acct  = st.text_input("ACCOUNT_NO", placeholder="เช่น Narats-E")
            with lg2:
                lg_code  = st.text_input("APP_CODE",   value="SANDBOX")
                lg_brok  = st.text_input("BROKER_ID",  value="SANDBOX")
                st.markdown("""
                <div style="background:rgba(99,102,241,.08);border:1.5px solid #c7d2fe;
                  border-radius:10px;padding:12px;font-size:13px;color:#818cf8;line-height:1.8;margin-top:8px">
                  📌 ข้อมูลจาก<br>
                  <b style="color:#4f46e5">developer.settrade.com</b><br>
                  SANDBOX = ทดสอบ<br>
                  ใส่รหัสโบรกเกอร์จริงเพื่อดูราคา real-time
                </div>
                """, unsafe_allow_html=True)
    
            submitted = st.form_submit_button("🔗 เชื่อมต่อ Settrade", use_container_width=True)
            if submitted:
                if not lg_id.strip() or not lg_sec.strip():
                    st.warning("กรุณาใส่ APP_ID และ APP_SECRET")
                else:
                    try:
                        with st.spinner("กำลังเชื่อมต่อ Settrade..."):
                            inv = Investor(
                                app_id=lg_id.strip(),
                                app_secret=lg_sec.strip(),
                                app_code=lg_code.strip() if lg_code.strip() else "SANDBOX",
                                broker_id=lg_brok.strip() if lg_brok.strip() else "SANDBOX",
                            )
                            # ── Detect API version ──────────────────────────────
                            # หลักการ: ลอง Equity(account_no) ก่อน
                            # ถ้า Equity มี get_candlestick → ใช้เป็น mkt_api
                            # ถ้าไม่มี → ลอง MarketData()
                            _acct      = lg_acct.strip()
                            mkt_api    = None
                            equity_api = None
                            rt_api     = None

                            # ── ลอง Equity ก่อน ──
                            if hasattr(inv, 'Equity'):
                                try:
                                    _eq = inv.Equity(_acct) if _acct else inv.Equity("")
                                except TypeError:
                                    try:    _eq = inv.Equity()
                                    except: _eq = None
                                except Exception:
                                    _eq = None

                                if _eq is not None:
                                    equity_api = _eq
                                    # ถ้า Equity มี get_candlestick ใช้เป็น mkt_api ด้วย
                                    if hasattr(_eq, 'get_candlestick'):
                                        mkt_api = _eq

                            # ── ถ้า Equity ไม่มี get_candlestick ลอง MarketData ──
                            if mkt_api is None:
                                for _attr in ['MarketData', 'Market', 'market_data', 'market']:
                                    if hasattr(inv, _attr):
                                        try:
                                            mkt_api = getattr(inv, _attr)()
                                            if hasattr(mkt_api, 'get_candlestick'):
                                                break
                                            mkt_api = None
                                        except Exception:
                                            pass

                            # ── Realtime ──
                            for _rattr in ['RealtimeDataConnection', 'Realtime', 'realtime']:
                                if hasattr(inv, _rattr):
                                    try:
                                        rt_api = getattr(inv, _rattr)()
                                        break
                                    except Exception:
                                        pass

                            if mkt_api is None:
                                avail = [a for a in dir(inv) if not a.startswith('_')]
                                eq_methods = [m for m in dir(equity_api) if not m.startswith('_')] if equity_api else []
                                raise AttributeError(
                                    f"ไม่พบ Market Data API ที่มี get_candlestick\n"
                                    f"Investor attrs: {avail}\n"
                                    f"Equity methods: {eq_methods}"
                                )
                            st.session_state.update(
                                st_ok=True,
                                st_mkt=mkt_api,        # MarketData API
                                st_equity=equity_api,  # Trading API
                                st_rt=rt_api,
                                st_inv=inv,
                                setup_done=True,
                                account_no=lg_acct.strip(),
                                app_id_saved="",
                                app_secret_saved="",
                            )
                            st.success("✅ เชื่อมต่อสำเร็จ!")
                            st.rerun()
                    except AttributeError as e:
                        st.error(str(e))
                    except Exception as e:
                        err = str(e)
                        st.error(f"เชื่อมต่อไม่สำเร็จ: {err}")
                        if "account_no" in err.lower() or "positional" in err.lower():
                            st.info("💡 กรุณาใส่ ACCOUNT_NO ด้วย เช่น Narats-E")
                        elif "401" in err:
                            st.warning("APP_ID หรือ APP_SECRET ไม่ถูกต้อง")
                        elif "403" in err:
                            st.warning("APP_CODE หรือ BROKER_ID ไม่ถูกต้อง")
        st.stop()


# ── Connected — แสดง status bar ──────────────────────────────
acct_disp = st.session_state.get("account_no","")
with st.expander(f"✅ เชื่อมต่อ Settrade แล้ว {('· บัญชี: '+acct_disp) if acct_disp else ''}", expanded=False):
    col_s1, col_s2 = st.columns([3,1])
    with col_s1:
        st.markdown("##### 🤖 AI วิเคราะห์ข่าว")
        ai_prov = st.radio("เลือก AI provider",
            ["gemini","claude"],
            format_func=lambda x: "🟢 Gemini (Google) — แนะนำ" if x=="gemini" else "🟣 Claude (Anthropic)",
            key="ai_provider", horizontal=True)
        if ai_prov == "gemini":
            gk = st.text_input("Gemini API Key", type="password",
                placeholder="AIzaSy...", key="gemini_key")
            if gk:
                st.success("✅ Gemini key พร้อม")
            else:
                st.caption("รับ key ฟรีที่ aistudio.google.com/apikey")
        else:
            st.caption("Claude API built-in ไม่ต้องใส่ key")
    with col_s2:
        if st.button("🔓 ออกจากระบบ", key="logout_top"):
            st.session_state.update(
                st_ok=False, st_mkt=None, st_rt=None, st_inv=None,
                setup_done=False, account_no=""
            )
            st.rerun()

# ── Read parameters from session state ───────────────────────
rsi_os = st.session_state.get("p_rsi_os", 35)
rsi_ob = st.session_state.get("p_rsi_ob", 65)
min_sc = st.session_state.get("p_min_sc", 55)
min_rr = st.session_state.get("p_min_rr", 1.2)


t1, t2, t3, t4 = st.tabs(["🔍 สแกนหุ้น","📊 วิเคราะห์","📡 Real-time","💼 Portfolio"])


# ══════════════════════════════════════════════════════════════
# TAB 1: SCANNER
# ══════════════════════════════════════════════════════════════
with t1:
    ca, cb = st.columns(2)
    with ca: mkt_sel = st.selectbox("ตลาด", list(MARKETS.keys()), key="sc_mkt")
    with cb: sig_sel = st.selectbox("สัญญาณ", ["ทั้งหมด","ซื้อ","ซื้อ+เฝ้าระวัง","ขาย"], key="sc_sig")

    # ── Parameters + Scan Tips ─────────────────────────────
    with st.expander("⚙️ Parameters & คำแนะนำการสแกน", expanded=False):
        pc1, pc2 = st.columns(2)
        with pc1:
            rsi_os = st.slider("RSI Oversold",   15, 45,
                int(st.session_state.get("_rsi_os_val", 35)), key="p_rsi_os")
            min_sc = st.slider("คะแนนขั้นต่ำ",  0, 100,
                int(st.session_state.get("_min_sc_val", 55)), key="p_min_sc")
        with pc2:
            rsi_ob = st.slider("RSI Overbought", 55, 85,
                int(st.session_state.get("_rsi_ob_val", 65)), key="p_rsi_ob")
            min_rr = st.slider("R/R ขั้นต่ำ",   0.5, 3.0,
                float(st.session_state.get("_min_rr_val", 1.2)), step=0.1, key="p_min_rr")

        st.markdown("---")
        st.markdown("**💡 Preset — เลือกรูปแบบตลาดเพื่อ Auto-fill ค่า**")
        tip_mode = st.selectbox("สถานะตลาดปัจจุบัน", list(SCAN_TIPS.keys()), key="tip_mode")
        tip = SCAN_TIPS[tip_mode]
        st.info(tip["คำอธิบาย"])
        tp1, tp2, tp3, tp4 = st.columns(4)
        tp1.metric("RSI Oversold",  tip["p_rsi_os"])
        tp2.metric("RSI Overbought",tip["p_rsi_ob"])
        tp3.metric("คะแนนขั้นต่ำ", tip["p_min_sc"])
        tp4.metric("R/R ขั้นต่ำ",  tip["p_min_rr"])
        if st.button("✅ ใช้ Preset นี้", key="apply_tip"):
            # ใช้ _val keys แทน widget keys โดยตรง
            st.session_state["_rsi_os_val"] = tip["p_rsi_os"]
            st.session_state["_rsi_ob_val"] = tip["p_rsi_ob"]
            st.session_state["_min_sc_val"] = tip["p_min_sc"]
            st.session_state["_min_rr_val"] = tip["p_min_rr"]
            st.success(f"✅ Applied preset: {tip_mode}")
            st.rerun()

        st.markdown("---")
        st.markdown("**📘 คำอธิบาย Indicators ที่ใช้สแกน**")
        st.table({
            "Indicator":   ["RSI(14)","MACD Hist","Stoch %K","BB %B","ADX","CCI","MFI","OBV","Williams%R","Vol Ratio"],
            "หมายความว่า": ["แรงซื้อ/ขาย","Momentum ทิศทาง","Momentum สั้น","ราคาใน BB","ความแรง Trend","Overbought/Oversold","เงินไหลเข้า/ออก","Volume ยืนยัน Trend","Momentum สั้น","Volume vs เฉลี่ย"],
            "สัญญาณซื้อ":  ["< 35 Oversold","บวก = ขาขึ้น","< 20 Oversold","< 0.2 ต่ำสุด","> 25 Trend ชัด","< -100 Oversold","< 30 Oversold","OBV > EMA","< -80 Oversold","> 1.5x มีแรง"],
        })

    rsi_os = st.session_state.get("p_rsi_os", 35)
    rsi_ob = st.session_state.get("p_rsi_ob", 65)
    min_sc = st.session_state.get("p_min_sc", 55)
    min_rr = float(st.session_state.get("p_min_rr", 1.2))

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
                      <div class="sym-lg">{sym} <span style="font-size:13px;color:#818cf8;font-family:'Sarabun',sans-serif">{name}</span></div>
                      <div style="margin-top:8px">{sig_ic(S['sig'])} <b style="color:#0f172a">{sig_th(S['sig'])}</b>
                        <span style="font-size:12px;color:#818cf8;margin-left:8px">R/R 1:{S['rr']}</span></div>
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
    # ค่าจากแท็บ ⚙️ ตั้งค่า
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
                q2  = {}
                df2 = None
                err_detail = ""
                if mkt_in == "SET":
                    if not st.session_state.get("st_ok"):
                        st.error("ยังไม่ได้เชื่อมต่อ Settrade — กรอก credential ใน ⚙️ ตั้งค่า")
                        st.stop()
                    mkt_api = st.session_state.st_mkt
                    # แสดง method จริงที่มีอยู่เพื่อ debug
                    avail_methods = [m for m in dir(mkt_api) if not m.startswith('_')]
                    try:
                        df2 = st_candles(sym2, mkt_api, 365)
                    except Exception as e:
                        err_detail = f"st_candles error: {e}\nEquity methods: {avail_methods}"
                    try:
                        q2 = st_quote(sym2, st.session_state.st_rt)
                    except Exception:
                        q2 = {}
                    if df2 is not None and q2:
                        rp = float(q2.get("last", q2.get("close", 0)))
                        if rp > 0:
                            df2.iloc[-1, df2.columns.get_loc("close")] = rp
                else:
                    try:
                        df2 = yf_data(sym2)
                    except Exception as e:
                        err_detail = f"yfinance error: {e}"

                I2 = calc_ind(df2)
                if not I2 or I2.get("price", 0) <= 0:
                    st.error(f"ดึงข้อมูล **{sym2}** ไม่ได้")
                    if err_detail:
                        st.code(err_detail)
                    if mkt_in == "SET":
                        mkt_api2 = st.session_state.get("st_mkt")
                        if mkt_api2:
                            methods = [m for m in dir(mkt_api2) if not m.startswith('_')]
                            st.info(f"Equity() มี methods: {methods}")
                    st.stop()
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
                  <div style="font-size:13px;color:#818cf8;margin-top:3px">{name2} &middot; {mkt_in}</div>
                  <div style="margin-top:10px">{sig_ic(S2['sig'])} <b style="font-size:16px;color:#0f172a">{sig_th(S2['sig'])}</b></div>
                  {('<div style="font-size:13px;color:#818cf8;margin-top:4px">Real-time: ฿'+fmt(float(q2.get("last",0)))+'</div>') if q2 else ""}
                </div>
                <div class="ring {sc_cl(S2['sc'])}">{S2['sc']}</div>
              </div>
              <div class="px-xl" style="color:{up_c}">{cur2}{fmt(p2)}</div>
              <div style="font-size:15px;color:{up_c};font-weight:700;margin-top:5px">
                {pstr(I2['chg'])} วันนี้
                <span style="color:#818cf8;font-weight:400"> &nbsp; {pstr(I2['chg5'],1)} 5 วัน</span>
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

            # ── Indicators ครบทุกตัว ──────────────────────────────
            st.markdown("#### 📊 Indicators ครบทุกตัว")

            def ind_box(lbl, val, bull=False, bear=False, note=""):
                c = "bull" if bull else "bear" if bear else "neut"
                b = "▲" if bull else "▼" if bear else "→"
                no = f'<div class="sig {c}">{b} {note}</div>' if note else ""
                return (f'<div class="ib"><div class="lbl">{lbl}</div>'
                        f'<div class="val {c}">{val}</div>{no}</div>')

            # Momentum
            st.markdown('<div style="font-size:12px;font-weight:700;color:#818cf8;'
                        'text-transform:uppercase;letter-spacing:1px;margin:14px 0 8px">Momentum</div>',
                        unsafe_allow_html=True)
            mi = st.columns(4)
            p2v = p2 or 1
            for col, lbl, val, bull, bear, note in [
                (mi[0],"RSI(14)", f"{I2.get('rsi',50):.1f}",
                 I2.get('rsi',50)<rsi_os, I2.get('rsi',50)>rsi_ob,
                 "Oversold" if I2.get('rsi',50)<rsi_os else "Overbought" if I2.get('rsi',50)>rsi_ob else "Neutral"),
                (mi[1],"RSI(6)",  f"{I2.get('rsi6',50):.1f}",
                 I2.get('rsi6',50)<25, I2.get('rsi6',50)>75, ""),
                (mi[2],"MACD Hist",f"{I2.get('macd',0):.4f}",
                 I2.get('macd',0)>0, I2.get('macd',0)<0, "Bullish" if I2.get('macd',0)>0 else "Bearish"),
                (mi[3],"MACD Line",f"{I2.get('macd_line',0):.4f}",
                 I2.get('macd_line',0)>0, I2.get('macd_line',0)<0, ""),
            ]:
                with col: st.markdown(ind_box(lbl,val,bull,bear,note), unsafe_allow_html=True)

            mi2 = st.columns(4)
            for col, lbl, val, bull, bear, note in [
                (mi2[0],"Stoch %K", f"{I2.get('stoch',50):.1f}",
                 I2.get('stoch',50)<20, I2.get('stoch',50)>80,
                 "Oversold" if I2.get('stoch',50)<20 else "Overbought" if I2.get('stoch',50)>80 else ""),
                (mi2[1],"Stoch %D", f"{I2.get('stochD',50):.1f}",
                 I2.get('stochD',50)<20, I2.get('stochD',50)>80, ""),
                (mi2[2],"CCI(20)",  f"{I2.get('cci',0):.1f}",
                 I2.get('cci',0)<-100, I2.get('cci',0)>100,
                 "Oversold" if I2.get('cci',0)<-100 else "Overbought" if I2.get('cci',0)>100 else ""),
                (mi2[3],"Williams%R",f"{I2.get('willr',-50):.1f}",
                 I2.get('willr',-50)<-80, I2.get('willr',-50)>-20,
                 "Oversold" if I2.get('willr',-50)<-80 else "Overbought" if I2.get('willr',-50)>-20 else ""),
            ]:
                with col: st.markdown(ind_box(lbl,val,bull,bear,note), unsafe_allow_html=True)

            mi3 = st.columns(4)
            for col, lbl, val, bull, bear, note in [
                (mi3[0],"ROC(10)", f"{I2.get('roc10',0):.2f}%",
                 I2.get('roc10',0)>0, I2.get('roc10',0)<-5, ""),
                (mi3[1],"ROC(20)", f"{I2.get('roc20',0):.2f}%",
                 I2.get('roc20',0)>0, I2.get('roc20',0)<-10, ""),
                (mi3[2],"MFI(14)", f"{I2.get('mfi',50):.1f}",
                 I2.get('mfi',50)<30, I2.get('mfi',50)>70,
                 "Oversold" if I2.get('mfi',50)<30 else "Overbought" if I2.get('mfi',50)>70 else ""),
                (mi3[3],"OBV Trend", I2.get('obv_trend','?').upper(),
                 I2.get('obv_trend')=='up', I2.get('obv_trend')=='down', ""),
            ]:
                with col: st.markdown(ind_box(lbl,val,bull,bear,note), unsafe_allow_html=True)

            # Moving Averages
            st.markdown('<div style="font-size:12px;font-weight:700;color:#818cf8;'
                        'text-transform:uppercase;letter-spacing:1px;margin:14px 0 8px">Moving Averages</div>',
                        unsafe_allow_html=True)
            ma1 = st.columns(4)
            for col, lbl, val, bull, bear, note in [
                (ma1[0],"vs SMA20",  pstr((p2/I2.get('sma20',p2v)-1)*100,1) if I2.get('sma20') else "--",
                 p2>I2.get('sma20',0), p2<I2.get('sma20',p2v*2), ""),
                (ma1[1],"vs SMA50",  pstr((p2/I2.get('sma50',p2v)-1)*100,1) if I2.get('sma50') else "--",
                 p2>I2.get('sma50',0), p2<I2.get('sma50',p2v*2), ""),
                (ma1[2],"vs SMA200", pstr((p2/I2.get('sma200',p2v)-1)*100,1) if I2.get('sma200') else "--",
                 p2>I2.get('sma200',0), p2<I2.get('sma200',p2v*2), ""),
                (ma1[3],"Trend",     f"{I2.get('trend_score',0)}/4 EMA",
                 I2.get('trend_score',0)>=3, I2.get('trend_score',0)<=1,
                 "Strong Bull" if I2.get('trend_score',0)==4 else "Strong Bear" if I2.get('trend_score',0)==0 else ""),
            ]:
                with col: st.markdown(ind_box(lbl,val,bull,bear,note), unsafe_allow_html=True)

            ma2 = st.columns(4)
            for col, lbl, val, bull, bear in [
                (ma2[0],"EMA9",   f"{cur2}{fmt(I2.get('ema9',0))}",  p2>I2.get('ema9',0), p2<I2.get('ema9',p2v*2)),
                (ma2[1],"EMA20",  f"{cur2}{fmt(I2.get('ema20',0))}", p2>I2.get('ema20',0), p2<I2.get('ema20',p2v*2)),
                (ma2[2],"EMA50",  f"{cur2}{fmt(I2.get('ema50',0))}", p2>I2.get('ema50',0), p2<I2.get('ema50',p2v*2)),
                (ma2[3],"EMA200", f"{cur2}{fmt(I2.get('ema200',0))}",p2>I2.get('ema200',0), p2<I2.get('ema200',p2v*2)),
            ]:
                with col: st.markdown(ind_box(lbl,val,bull,bear), unsafe_allow_html=True)

            gc = I2.get('golden_cross', False)
            st.markdown(
                f'<div class="ib" style="text-align:left;padding:10px 14px">' +
                ('<span class="bull">✅ Golden Cross — EMA50 > EMA200 (Bullish)</span>' if gc else
                 '<span class="bear">❌ Death Cross — EMA50 < EMA200 (Bearish)</span>') +
                '</div>', unsafe_allow_html=True)

            # Volatility
            st.markdown('<div style="font-size:12px;font-weight:700;color:#818cf8;'
                        'text-transform:uppercase;letter-spacing:1px;margin:14px 0 8px">Volatility & Bands</div>',
                        unsafe_allow_html=True)
            vi = st.columns(4)
            for col, lbl, val, bull, bear, note in [
                (vi[0],"BB %B",    f"{I2.get('bb_pct',0.5):.3f}",
                 I2.get('bb_pct',0.5)<0.2, I2.get('bb_pct',0.5)>0.8, ""),
                (vi[1],"BB Width", f"{I2.get('bb_w',0):.4f}",
                 False, False, "⚡ Squeeze!" if I2.get('bb_w',1)<0.05 else ""),
                (vi[2],"ATR(14)",  f"{cur2}{fmt(I2.get('atr',0))}",  False, False, ""),
                (vi[3],"ATR(7)",   f"{cur2}{fmt(I2.get('atr7',0))}", False, False, ""),
            ]:
                with col: st.markdown(ind_box(lbl,val,bull,bear,note), unsafe_allow_html=True)

            # Volume & Trend
            st.markdown('<div style="font-size:12px;font-weight:700;color:#818cf8;'
                        'text-transform:uppercase;letter-spacing:1px;margin:14px 0 8px">Volume & Trend Strength</div>',
                        unsafe_allow_html=True)
            ti = st.columns(4)
            for col, lbl, val, bull, bear, note in [
                (ti[0],"Vol Ratio", f"{I2.get('vol_r',1):.2f}x",
                 I2.get('vol_r',1)>1.5, I2.get('vol_r',1)<0.5, "High" if I2.get('vol_r',1)>1.5 else "Low" if I2.get('vol_r',1)<0.5 else ""),
                (ti[1],"VWAP",  f"{cur2}{fmt(I2.get('vwap',0))}",
                 p2>I2.get('vwap',0), p2<I2.get('vwap',p2v*2),
                 "Above" if p2>I2.get('vwap',0) else "Below"),
                (ti[2],"ADX",   f"{I2.get('adx',0):.1f}",
                 I2.get('adx',0)>25 and I2.get('dip',0)>I2.get('dim',0),
                 I2.get('adx',0)>25 and I2.get('dim',0)>I2.get('dip',0),
                 "Uptrend" if I2.get('adx',0)>25 and I2.get('dip',0)>I2.get('dim',0) else
                 "Downtrend" if I2.get('adx',0)>25 else "Sideways"),
                (ti[3],"DI+/DI-", f"{I2.get('dip',0):.1f}/{I2.get('dim',0):.1f}",
                 I2.get('dip',0)>I2.get('dim',0), I2.get('dim',0)>I2.get('dip',0), ""),
            ]:
                with col: st.markdown(ind_box(lbl,val,bull,bear,note), unsafe_allow_html=True)

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
            <div style="background:#ede9fe;border:1.5px solid #c4b5fd;
              border-radius:10px;padding:12px 16px;margin-top:10px;
              display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:14px;color:#818cf8">Risk / Reward</span>
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
            <div style="display:flex;justify-content:space-between;font-size:12px;color:#818cf8;margin-bottom:5px">
              <span>Low {cur2}{fmt(I2['l52'])}</span>
              <span style="color:#0f172a;font-weight:700">{p52p:.0f}% จากต่ำสุด</span>
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
            with st.spinner(f"{provider_label} กำลังค้นข่าว 1 เดือนล่าสุดและวิเคราะห์... (อาจใช้เวลา 20-40 วิ)"):
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
                  <span style="font-size:13px;color:#818cf8;margin-left:8px">{mkt3}</span>
                  <div style="margin-top:6px">{sig_ic(sig3)} <b style="color:#0f172a">{sig_th(sig3)}</b>
                    <span style="font-size:12px;color:#818cf8;margin-left:8px">Score {sc3}</span></div>
                </div>
                <div style="text-align:right">
                  <div style="font-size:22px;font-weight:700;font-family:'IBM Plex Mono',monospace;color:{up_c3}">
                    {cur3}{fmt(price3) if price3 else '--'}</div>
                  <div style="font-size:13px;color:{up_c3};font-weight:700">{pstr(chg3)}</div>
                </div>
              </div>
              <div style="background:#d1d5db;border-radius:3px;height:4px;margin-top:10px">
                <div style="width:{sc3}%;height:4px;border-radius:3px;background:{sc_co(sc3)}"></div>
              </div>
              <div style="font-size:12px;color:#818cf8;margin-top:5px">
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
            # Portfolio API
            port    = None
            acct_no = st.session_state.get("account_no", "")

            if hasattr(inv, 'Equity'):
                try:
                    port = inv.Equity(acct_no) if acct_no else inv.Equity("")
                except TypeError:
                    port = inv.Equity()
            elif hasattr(inv, 'Portfolio') and callable(inv.Portfolio):
                try:    port = inv.Portfolio(acct_no) if acct_no else inv.Portfolio()
                except: port = getattr(inv, 'Portfolio', None)
            elif hasattr(inv, 'portfolio'):
                port = inv.portfolio

            if port is None:
                st.error("ไม่พบ Portfolio API — ลอง pip install settrade-v2 --upgrade")
                st.stop()

            # Balance
            st.markdown("#### 💰 สรุปบัญชี")
            try:
                acct = st.session_state.get("account_no", "")
                bal = None
                for m in ['get_account_balance', 'get_balance', 'get_account']:
                    if hasattr(port, m):
                        try:
                            fn = getattr(port, m)
                            bal = fn(acct) if acct else fn()
                            if bal: break
                        except Exception:
                            pass
                if bal:
                    b = bal[0] if isinstance(bal, list) else bal
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("วงเงินทั้งหมด", f"฿{float(b.get('credit_limit', b.get('line', 0))):,.0f}")
                    c2.metric("ใช้ไปแล้ว",     f"฿{float(b.get('used_amount',  b.get('call_force_margin', 0))):,.0f}")
                    c3.metric("คงเหลือ",        f"฿{float(b.get('available_balance', b.get('net_balance', 0))):,.0f}")
                    c4.metric("กำไร/ขาดทุน",   f"฿{float(b.get('unrealized_pl', b.get('unrealized', 0))):,.0f}")
                else:
                    st.info("ไม่พบข้อมูลบัญชี")
            except Exception as e:
                st.info(f"Balance: {e}")

            # Holdings
            st.markdown("#### 📋 หุ้นที่ถืออยู่")
            try:
                acct = st.session_state.get("account_no", "")
                h = None
                for m in ['get_portfolio', 'get_portfolio_by_account_no', 'get_holding']:
                    if hasattr(port, m):
                        try:
                            fn = getattr(port, m)
                            h = fn(acct) if acct else fn()
                            if h: break
                        except Exception:
                            pass
                if h:
                    df_h = pd.DataFrame(h if isinstance(h, list) else [h])
                    st.dataframe(df_h, use_container_width=True)
                else:
                    st.info("ไม่มีหุ้นในพอร์ต")
            except Exception as e:
                st.info(f"Portfolio: {e}")

            # Orders
            st.markdown("#### 📝 คำสั่งซื้อขาย")
            try:
                acct = st.session_state.get("account_no", "")
                o = None
                for m in ['get_orders', 'get_order_list', 'get_order']:
                    if hasattr(port, m):
                        try:
                            fn = getattr(port, m)
                            o = fn(acct) if acct else fn()
                            if o: break
                        except Exception:
                            pass
                if o:
                    df_o = pd.DataFrame(o if isinstance(o, list) else [o])
                    st.dataframe(df_o, use_container_width=True)
                else:
                    st.info("ไม่มีคำสั่งค้างอยู่")
            except Exception as e:
                st.info(f"Orders: {e}")

            # Trade history
            st.markdown("#### 📈 ประวัติการซื้อขาย")
            try:
                acct = st.session_state.get("account_no", "")
                tr2 = None
                for m in ['get_trades', 'get_trade_list', 'get_trade']:
                    if hasattr(port, m):
                        try:
                            fn = getattr(port, m)
                            tr2 = fn(acct) if acct else fn()
                            if tr2: break
                        except Exception:
                            pass
                if tr2:
                    df_t = pd.DataFrame(tr2 if isinstance(tr2, list) else [tr2])
                    st.dataframe(df_t, use_container_width=True)
                else:
                    st.info("ไม่มีข้อมูล trade history")
            except Exception as e:
                st.info(f"Trades: {e}")




st.markdown('<div style="text-align:center;font-size:11px;color:#d1d5db;margin-top:24px">'
            'ใช้เพื่อการศึกษาเท่านั้น · ไม่ใช่คำแนะนำการลงทุน</div>',
            unsafe_allow_html=True)
