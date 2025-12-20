
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys

# Load config directly or use hardcoded for test
# We will try to import from config_local to use the same creds
sys.path.append(os.getcwd())

try:
    from app.config_local import LocalConfig
    USERNAME = LocalConfig.MAIL_USERNAME
    PASSWORD = LocalConfig.MAIL_PASSWORD
    print(f"Loaded credentials for: {USERNAME}")
except ImportError:
    print("Could not load config_local.py. Please ensure it exists.")
    sys.exit(1)
except AttributeError:
    print("config_local.py exists but missing MAIL_USERNAME or MAIL_PASSWORD.")
    sys.exit(1)

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def test_send_email():
    sender_email = USERNAME
    receiver_email = USERNAME # Send to self
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "Test Email from PythonAnywhere (Sync)"

    body = "This is a test email to verify SMTP configuration and connectivity."
    msg.attach(MIMEText(body, 'plain'))

    print(f"Connecting to {SMTP_SERVER}:{SMTP_PORT}...")
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        print("Connected.")
        
        print("Starting TLS...")
        server.starttls()
        print("TLS started.")
        
        print(f"Logging in as {USERNAME}...")
        server.login(USERNAME, PASSWORD)
        print("Logged in successfully.")
        
        text = msg.as_string()
        print("Sending email...")
        server.sendmail(sender_email, receiver_email, text)
        print("Email sent successfully!")
        
        server.quit()
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_send_email()
