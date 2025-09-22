# otp/utils.py
import pyotp
from django.conf import settings
from otp.models import OTP
import logging
from emails.send_otp_email import send_email_via_smtp  # Import the email sending function

logger = logging.getLogger(__name__)

def generate_otp():
    totp = pyotp.TOTP('base32secret3232', interval=300)
    return totp.now()

def prepare_email_data(email, otp_code):
    subject = 'Bestätigung Ihrer E-Mail-Adresse'
    plain_message = f'Ihr Bestätigungscode: {otp_code}\nDieser Code ist 5 Minuten lang gültig.'
    
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }}
            .container {{ width: 100%; max-width: 600px; margin: 20px auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); }}
            .header {{ background-color: #007bff; color: #ffffff; padding: 10px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ padding: 20px; text-align: center; }}
            .otp-code {{ font-size: 24px; font-weight: bold; color: #007bff; letter-spacing: 2px; margin: 20px 0; }}
            .footer {{ font-size: 12px; color: #777777; text-align: center; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>E-Mail-Bestätigung</h2>
            </div>
            <div class="content">
                <p>Guten Tag,</p>
                <p>Bitte verwenden Sie den folgenden Code, um Ihre E-Mail-Adresse zu bestätigen:</p>
                <div class="otp-code">{otp_code}</div>
                <p>Dieser Code ist <strong>5 Minuten</strong> lang gültig.</p>
            </div>
            <div class="footer">
                <p>© 2025 Ihr Unternehmen.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return {
        'subject': subject,
        'plain_message': plain_message,
        'html_message': html_message,
        'sender_email': 'm10551691@gmail.com', 
        'receiver_email': email
    }

def send_otp_to_user(email):
    otp_code = generate_otp()
    OTP.objects.create(email=email, otp_code=otp_code)

    email_data = prepare_email_data(email, otp_code)
    
    try:
        result = send_email_via_smtp(email_data)
        if not result and settings.DEBUG:
            print("[DEBUG] Email sending failed (check SMTP logs)")
        return result
    except Exception as e:
        logger.error(f"Email sending error: {str(e)}")
        if settings.DEBUG:
            print(f"[DEBUG] Email error details: {str(e)}")
        return False

    
    return send_email_via_smtp(email_data)