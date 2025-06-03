from email.mime.text import MIMEText
import smtplib


def send_reset_email(to_email: str, token: str):
    print(f"Attempting to send reset email to: {to_email}")
    try:
        reset_link = f"http://localhost:8000/reset-password?token={token}"
        subject = "Password Reset Request"
        body = f"Click the link to reset your password: {reset_link}"

        message = MIMEText(body)
        message["Subject"] = subject
        message["From"] = "yourgmail@gmail.com"
        message["To"] = to_email

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("yourgmail@gmail.com", "your-app-password")
            server.sendmail("yourgmail@gmail.com", to_email, message.as_string())

        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Error sending email: {e}")
