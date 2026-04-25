import streamlit as st
import logging
from settrade_v2 import Investor

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- UI: Sidebar สำหรับกรอกข้อมูลใหม่ทั้งหมด ---
st.sidebar.header("🔑 Settrade API Configuration")

with st.sidebar:
    # ลบค่า value ออกเพื่อให้เป็นช่องว่าง (Empty string)
    input_app_id = st.text_input("App ID", value="")
    input_app_secret = st.text_input("App Secret", value="", type="password")
    input_app_code = st.text_input("App Code", value="", help="ใส่ 'SANDBOX' สำหรับระบบทดสอบ")
    input_broker_id = st.text_input("Broker ID", value="")
    input_account_no = st.text_input("Account No", value="")
    input_pin = st.text_input("PIN", value="", type="password")

    connect_btn = st.button("Connect to Settrade")

# --- Class สำหรับจัดการ Robot (v2 compatible) ---
class SettradeRobot:
    def __init__(self, config):
        try:
            # ใช้เฉพาะ 4 parameter หลักตามมาตรฐาน SDK v2
            self.investor = Investor(
                app_id=config['app_id'],
                app_secret=config['app_secret'],
                app_code=config['app_code'],
                broker_id=config['broker_id']
            )
            self.equity = self.investor.Equity(account_no=config['account_no'])
            self.pin = config['pin']
            st.success(f"✅ เชื่อมต่อบัญชี {config['account_no']} สำเร็จ!")
        except Exception as e:
            st.error(f"❌ การเชื่อมต่อล้มเหลว: {e}")
            raise

    def get_portfolio(self):
        try:
            return self.equity.get_portfolios()
        except Exception as e:
            st.error(f"ไม่สามารถดึงข้อมูลพอร์ตได้: {e}")

# --- ส่วนแสดงผลหลัก ---
st.title("🤖 AI Trading Bot Dashboard")

if connect_btn:
    # ตรวจสอบว่ากรอกข้อมูลครบหรือไม่
    if not all([input_app_id, input_app_secret, input_app_code, input_broker_id, input_account_no, input_pin]):
        st.warning("⚠️ กรุณากรอกข้อมูลให้ครบทุกช่อง")
    else:
        current_config = {
            "app_id": input_app_id,
            "app_secret": input_app_secret,
            "app_code": input_app_code,
            "broker_id": input_broker_id,
            "account_no": input_account_no,
            "pin": input_pin
        }
        
        # เก็บใน Session State
        st.session_state.bot = SettradeRobot(current_config)

# ตรวจสอบสถานะการเชื่อมต่อ
if "bot" in st.session_state:
    st.write("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 เช็คพอร์ตการลงทุน"):
            port_data = st.session_state.bot.get_portfolio()
            st.write("### ข้อมูลพอร์ต")
            st.json(port_data)
            
    with col2:
        if st.button("🔄 ล้างการเชื่อมต่อ"):
            del st.session_state.bot
            st.rerun()
else:
    st.info("💡 กรุณากรอกข้อมูล API Credentials ที่แถบด้านข้างเพื่อเริ่มต้นใช้งาน")
