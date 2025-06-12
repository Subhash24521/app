from email.message import EmailMessage
import smtplib
from app.core.config import EMAIL_ADDRESS, EMAIL_PASSWORD

def send_reset_email(to_email: str, token: str):
    msg = EmailMessage()
    msg['Subject'] = 'Reset Your Password'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email

    reset_link = f"https://piano-app-q7f6.onrender.com/reset-password?token={token}"
    msg.set_content(f"Click this link to reset your password:\n{reset_link}")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("✅ Reset email sent to:", to_email)
    except Exception as e:
        print("❌ Email sending failed:", e)
