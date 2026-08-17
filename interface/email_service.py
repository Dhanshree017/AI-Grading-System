import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import re

def send_gibo_email(recipient_email, student_name, report_data, attachment_data=None, attachment_filename="ScoreReport.pdf"):
    SENDER_EMAIL = "Enter sender email"  
    SENDER_PASSWORD = "Enter your password"  
    
    msg = MIMEMultipart()
    msg['From'] = f"GIBO AI Grading <{SENDER_EMAIL}>"
    msg['To'] = recipient_email
    msg['Subject'] = f"Academic Performance Report - {student_name}"

    # Clean the report text
    clean_report = re.sub(r'#+', '', report_data)
    clean_report = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_report)

    html_body = f"""
    <html>
    <body style="font-family: sans-serif;">
        <h2 style="color: #2d1b69;">Hello {student_name},</h2>
        <p>Your evaluation is complete. Your detailed <b>Score Table</b> is attached to this email as a PDF.</p>
        <div style="background-color: #f5f0ff; padding: 20px; border-radius: 10px; border-left: 5px solid #7b2cff; color: #333; line-height: 1.6;">
            {clean_report.replace(chr(10), '<br>')}
        </div>
        <p>Keep learning! ✨</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    # ATTACHMENT LOGIC
    if attachment_data is not None:
        part = MIMEBase('application', 'pdf') # Changed to explicit PDF type
        part.set_payload(attachment_data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{attachment_filename}"')
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False