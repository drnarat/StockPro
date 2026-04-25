# AI Trading Bot with Settrade Open API v2

โปรเจกต์พัฒนาหุ่นยนต์เทรดหุ้นอัตโนมัติ เชื่อมต่อกับระบบ Settrade Open API v2 รองรับการทำงานในระบบ Sandbox และ Production

## การติดตั้ง (Installation)
1. Clone repository นี้ลงเครื่อง
2. สร้าง Virtual Environment: `python -m venv venv`
3. ติดตั้ง Library: `pip install -r requirements.txt`
4. สร้างไฟล์ `config.py` โดยคัดลอกรูปแบบจากตัวอย่างด้านล่าง

## การใช้งาน (Usage)
แก้ไขข้อมูลใน `config.py` แล้วรันโปรแกรม:
```bash
python trading_bot.py
