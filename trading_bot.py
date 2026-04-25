import logging
from settrade_v2 import Investor
from config import SETTRADE_CONFIG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SettradeRobot:
    def __init__(self):
        conf = SETTRADE_CONFIG
        try:
            self.investor = Investor(
                app_id=conf["APP_ID"],
                app_secret=conf["APP_SECRET"],
                app_code=conf["APP_CODE"],
                broker_id=conf["BROKER_ID"],
                is_sandbox=conf["IS_SANDBOX"]
            )
            self.equity = self.investor.Equity(account_no=conf["ACCOUNT_NO"])
            self.pin = conf["PIN"]
            logger.info(f"✅ Bot initialized for account: {conf['ACCOUNT_NO']}")
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            raise

    def get_portfolio(self):
        return self.equity.get_portfolios()

    def place_order(self, symbol, side, volume, price):
        try:
            return self.equity.place_order(
                symbol=symbol.upper(),
                side=side.capitalize(),
                volume=volume,
                price=price,
                pin=self.pin,
                order_type="Limit"
            )
        except Exception as e:
            logger.error(f"❌ Order error: {e}")

if __name__ == "__main__":
    bot = SettradeRobot()
    # ดร. สามารถทดสอบคำสั่งได้ที่นี่
