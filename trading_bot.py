import streamlit as st
import logging
from settrade_v2 import Investor

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- UI: Sidebar สำหรับกรอก Configuration ---
st.sidebar.header("🔑 Settrade API Configuration")

with st.sidebar:
    input_app_id = st.text_input("App ID", value="MPRZz1Hymo6nR50A")
    input_app_secret = st.text_input("App Secret", value="Te/3LKXBb+IM20T/ygcFAMWXjIgkadJ+o1cDstkjRDQ=", type="password")
    input_app_code = st.text_input("App Code", value="SANDBOX")
    input_broker_id = st.text_input("Broker ID", value="SANDBOX")
    input_account_no = st.text_input("Account No", value="Narats-E")
    input_pin = st.text_input("PIN", value="111111", type="password")
    input_is_sandbox = st.checkbox("Sandbox Mode", value=True)

    connect_btn = st.button("Connect to Settrade")

# --- Class สำหรับจัดการ Robot ---
class SettradeRobot:
    def __init__(self, config):
        try:
            self.investor = Investor(
                app_id=config['app_id'],
                app_secret=config['app_secret'],
                app_code=config['app_code'],
                broker_id=config['broker_id'],
                is_sandbox=config['is_sandbox']
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
    # รวบรวมค่าจาก Input มาใส่ใน Dictionary
    current_config = {
        "app_id": input_app_id,
        "app_secret": input_app_secret,
        "app_code": input_app_code,
        "broker_id": input_broker_id,
        "account_no": input_account_no,
        "pin": input_pin,
        "is_sandbox": input_is_sandbox
    }
    
    # บันทึกลงใน Session State เพื่อให้ใช้งานได้ตลอดการรันแอป
    st.session_state.bot = SettradeRobot(current_config)

# ตรวจสอบว่ามีการเชื่อมต่อแล้วหรือไม่
if "bot" in st.session_state:
    if st.button("เช็คพอร์ตปัจจุบัน"):
        port_data = st.session_state.bot.get_portfolio()
        st.write("### ข้อมูลพอร์ตการลงทุน")
        st.json(port_data)
else:
    st.info("กรุณากรอกข้อมูลที่แถบด้านข้างและกดปุ่ม Connect เพื่อเริ่มต้น")
