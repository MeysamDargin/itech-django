import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from decouple import config

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def send_email_via_smtp(email_data):
    try:
        EMAIL_HOST = config("EMAIL_HOST")
        EMAIL_PORT = config("EMAIL_PORT", cast=int)
        MAIL_USER = config("MAIL_USER")
        MAIL_PASSWORD = config("MAIL_PASSWORD")

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.set_debuglevel(1)
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = email_data['subject']
        msg['From'] = email_data.get('sender_email', MAIL_USER)
        msg['To'] = email_data['receiver_email']
        
        part1 = MIMEText(email_data['plain_message'], 'plain')
        part2 = MIMEText(email_data['html_message'], 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # --- اتصال و شروع TLS ---
        server.ehlo()
        server.starttls()
        server.ehlo()
        
        # --- لاگین با env ---
        server.login(MAIL_USER, MAIL_PASSWORD)
        
        # --- ارسال ایمیل ---
        server.sendmail(
            msg['From'],
            msg['To'],
            msg.as_string()
        )
        
        server.quit()
        return True
        
    except smtplib.SMTPException as e:
        if hasattr(e, 'smtp_error'):
            logger.error(f"SMTP Error: {e.smtp_error}")
        return False
    except Exception as e:
        logger.error(f"General Error: {e}", exc_info=True)
        return False
