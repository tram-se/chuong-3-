import os
import shutil
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import schedule
import time

# Load biến môi trường từ file .env
load_dotenv()

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# Định nghĩa đường dẫn
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'database')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')

# Tạo thư mục backups nếu chưa tồn tại
os.makedirs(BACKUP_DIR, exist_ok=True)

def send_email(success: bool, message: str, attachments: list = None):
    subject = "Backup thành công" if success else "Backup thất bại"

    html_message = f"""
<html>
<head>
  <style>
    body {{
        font-family: Arial, sans-serif;
        background-color: #f4f4f4;
        padding: 20px;
    }}
    .container {{
        background-color: #fff;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #ccc;
    }}
    h3 {{
        color: {"green" if success else "red"};
    }}
    p {{
        white-space: pre-line;
        font-size: 14px;
        color: #333;
    }}
  </style>
</head>
<body>
  <div class="container">
    <h3>{subject}</h3>
    <p>{message}</p>
  </div>
</body>
</html>
"""

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    msg.attach(MIMEText(html_message, "html"))

    # Đính kèm file nếu có
    if attachments:
        from email.mime.base import MIMEBase
        from email import encoders

        for filepath in attachments:
            try:
                with open(filepath, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(filepath)}",
                )
                msg.attach(part)
            except Exception as e:
                print(f"⚠️ Lỗi khi đính kèm file {filepath}: {e}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✅ Đã gửi email thông báo kèm file backup.")
    except Exception as e:
        print("❌ Gửi email thất bại:", e)


def backup_files():
    try:
        if not os.path.exists(DB_DIR):
            raise FileNotFoundError(f"Thư mục '{DB_DIR}' không tồn tại.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        files_backed_up = []
        attachment_paths = []

        for filename in os.listdir(DB_DIR):
            if filename.endswith(".sqlite3") or filename.endswith(".sql"):
                src_path = os.path.join(DB_DIR, filename)
                backup_name = f"{filename}_{timestamp}"
                dst_path = os.path.join(BACKUP_DIR, backup_name)
                shutil.copy2(src_path, dst_path)
                files_backed_up.append(backup_name)
                attachment_paths.append(dst_path)

        if files_backed_up:
            message = "Backup thành công cho các file:\n" + "\n".join(files_backed_up)
        else:
            message = "Không có file .sqlite3 hoặc .sql nào để backup."

        send_email(True, message, attachments=attachment_paths)
        print("✅ Backup hoàn tất.")
    except Exception as e:
        error_msg = f"Lỗi khi backup: {str(e)}"
        send_email(False, error_msg)
        print("❌", error_msg)


# Lên lịch chạy mỗi ngày lúc 00:00
schedule.every().day.at("14:17").do(backup_files)

print("⏳ Đang chạy... đợi đến 00:00 để thực hiện backup...")

while True:
    schedule.run_pending()
    time.sleep(30)
    