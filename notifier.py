import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

# 修改为你的邮箱配置
EMAIL_CONFIG = {
    "sender": "m13811282241@163.com",          # 发送方邮箱
    "password": "SPv88H76LxgZQcdW",           # 邮箱 SMTP 授权码
    "smtp_server": "smtp.163.com",           # SMTP 服务器地址
    "port": 465,                                 # 465=SSL，587=TLS
    "receiver": "m13811282241@163.com"  # 接收方邮箱
}

def send_email(subject, body):
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = formataddr(("Trading Bot", EMAIL_CONFIG["sender"]))
        msg["To"] = formataddr(("Trader", EMAIL_CONFIG["receiver"]))
        msg["Subject"] = subject

        server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"])
        server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
        server.sendmail(EMAIL_CONFIG["sender"], [EMAIL_CONFIG["receiver"]], msg.as_string())
        server.quit()
        print("✅ Email sent:", subject)
    except Exception as e:
        print("❌ Email failed:", e)
