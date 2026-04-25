import streamlit as st
import logging
from settrade_v2 import Investor

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- UI: Sidebar สำหรับกรอกข้อมูล ---
st.sidebar.header("🔑 Settrade API Configuration")

with st.sidebar:
    input_app_id = st.text_input("App ID", value="")
    input_app_secret = st.text_input("App Secret", value="", type="password")
    input_app_code = st.text_input("App Code", value="", help="ใส่ 'SANDBOX' สำหรับระบบทดสอบ")
    input_broker_id = st.text_input("Broker ID", value="")
    input_account_no = st.text_input("Account No", value="")
    input_pin = st.text_input("PIN", value="", type="password")

    connect_btn = st.sidebar.button("Connect to Settrade")

# --- Class สำหรับจัดการ Robot ---
class SettradeRobot:
    def __init__(self, config):
        try:
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
            return None

    def place_order(self, symbol, side, volume, price):
        try:
            return self.equity.place_order(
                symbol=symbol.upper(),
                side=side,
                volume=volume,
                price=price,
                pin=self.pin,
                order_type="Limit"
            )
        except Exception as e:
            st.error(f"❌ ส่งคำสั่งล้มเหลว: {e}")
            return None

# --- ส่วนแสดงผลหลัก ---
st.title("🤖 AI Trading Bot Dashboard")

if connect_btn:
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
        st.session_state.bot = SettradeRobot(current_config)

# ตรวจสอบสถานะการเชื่อมต่อ
if "bot" in st.session_state:
    st.write("---")
    
    # ส่วนเช็คพอร์ต
    if st.button("📊 เช็คพอร์ตการลงทุน"):
        port_data = st.session_state.bot.get_portfolio()
        if port_data:
            st.write("### ข้อมูลพอร์ต")
            st.json(port_data)

    st.write("---")
    st.subheader("🛒 ส่งคำสั่งซื้อขาย (Test Order)")
    
    # ฟอร์มซื้อขาย (แก้ไขฟังก์ชันปุ่มแล้ว)
    with st.form("order_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol = st.text_input("ชื่อหุ้น", value="PTT")
        with col2:
            side = st.selectbox("ฝั่ง", ["Buy", "Sell"])
        with col3:
            volume = st.number_input("จำนวนหุ้น", min_value=100, step=100, value=100)
            
        price = st.number_input("ราคาต่อหุ้น", min_value=0.0, step=0.25, value=35.00)
        
        # ฟังก์ชันที่ถูกต้องคือ st.form_submit_button
        submit_order = st.form_submit_button("ส่งคำสั่ง Order")

        if submit_order:
            order_res = st.session_state.bot.place_order(symbol, side, volume, price)
            if order_res:
                st.success(f"ส่งคำสั่ง {side} {symbol} เรียบร้อยแล้ว!")
                st.json(order_res)

    if st.button("🔄 ล้างการเชื่อมต่อ"):
        del st.session_state.bot
        st.rerun()
else:
    st.info("💡 กรุณากรอกข้อมูล API Credentials ที่แถบด้านข้างเพื่อเริ่มต้นใช้งาน")
