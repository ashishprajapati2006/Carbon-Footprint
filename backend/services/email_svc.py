import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from core.config import settings

logger = logging.getLogger("ecopilot.email_svc")

class EmailService:
    @staticmethod
    async def send_report_email(user_email: str, report_data: dict, pdf_bytes: bytes = None) -> bool:
        """
        Sends an HTML summary of the carbon report to the user.
        Attaches the PDF report if pdf_bytes are provided.
        Falls back to logging if SMTP settings are unconfigured or dummy.
        """
        report_type = report_data.get("report_type", "monthly").capitalize()
        subject = f"EcoPilot AI - Your {report_type} Sustainability Report"
        
        # 1. Compile simple but beautiful HTML report body
        trend = report_data.get("carbon_trend", {})
        total_co2 = trend.get("total_co2_kg", 0.0)
        pct_change = trend.get("percentage_change", 0.0)
        direction = trend.get("direction", "stable")
        
        dir_text = "increased 📈" if direction == "up" else "decreased 📉" if direction == "down" else "remained stable ➡️"
        ai_summary_html = report_data.get("ai_summary", "No AI analysis available.").replace("\n", "<br/>")
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <div style="background-color: #10b981; color: white; padding: 15px; text-align: center; border-radius: 6px 6px 0 0;">
                    <h2 style="margin: 0;">EcoPilot AI Sustainability Performance</h2>
                </div>
                <div style="padding: 20px;">
                    <p>Hello,</p>
                    <p>Here is your weekly/monthly executive carbon footprint report compiled by EcoPilot AI.</p>
                    
                    <div style="background-color: #f8fafc; border-left: 4px solid #10b981; padding: 15px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #10b981;">🌱 AI Summary Review</h3>
                        <p style="font-style: italic; color: #475569;">{ai_summary_html}</p>
                    </div>
                    
                    <h3>📊 Performance Metrics</h3>
                    <ul>
                        <li><b>Total Footprint:</b> {total_co2:.2f} kg CO2e</li>
                        <li><b>Trend compared to prior period:</b> {dir_text} by {pct_change:.1f}%</li>
                    </ul>
                    
                    <p>Please find the attached PDF report for a full detailed breakdown of recommendations, achievements, and future predictions.</p>
                    <br/>
                    <p>Best regards,<br/><b>EcoPilot AI Team</b></p>
                </div>
                <div style="background-color: #f1f5f9; padding: 10px; text-align: center; font-size: 11px; color: #64748b; border-radius: 0 0 6px 6px;">
                    Powered by EcoPilot Sustainability Engine. You received this because you are registered with EcoPilot.
                </div>
            </body>
        </html>
        """

        # 2. Check if SMTP configuration is configured
        is_dummy = (
            settings.email_user == "user@example.com" or 
            settings.email_password == "password" or
            settings.email_host == "smtp.gmail.com" and settings.email_user == "user@example.com"
        )
        
        if is_dummy:
            logger.warning("SMTP configuration is using default/dummy values. Falling back to log-based simulation.")
            logger.info("================== EMAIL SIMULATION LOG ==================")
            logger.info(f"TO: {user_email}")
            logger.info(f"SUBJECT: {subject}")
            logger.info(f"BODY:\n{html_content}")
            if pdf_bytes:
                logger.info(f"ATTACHMENT: report_{report_data.get('_id', 'new')}.pdf ({len(pdf_bytes)} bytes)")
            logger.info("==========================================================")
            return True

        # 3. Connect and send real email
        try:
            logger.info(f"Sending real report email via {settings.email_host}:{settings.email_port} to {user_email}...")
            
            msg = MIMEMultipart()
            msg["From"] = settings.email_user
            msg["To"] = user_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_content, "html"))
            
            if pdf_bytes:
                part = MIMEApplication(pdf_bytes, Name=f"EcoPilot_Report_{report_type}.pdf")
                part['Content-Disposition'] = f'attachment; filename="EcoPilot_Report_{report_type}.pdf"'
                msg.attach(part)
                
            # Connect SMTP server
            server = smtplib.SMTP(settings.email_host, settings.email_port)
            server.ehlo()
            if settings.email_port == 587:
                server.starttls()
                server.ehlo()
            server.login(settings.email_user, settings.email_password)
            server.sendmail(settings.email_user, user_email, msg.as_string())
            server.close()
            
            logger.info(f"Successfully sent report email to {user_email}.")
            return True
        except Exception as e:
            logger.error(f"Failed to send report email via SMTP: {e}. Falling back to simulation logs.")
            logger.info("================== EMAIL FALLBACK LOG ==================")
            logger.info(f"TO: {user_email}")
            logger.info(f"SUBJECT: {subject}")
            logger.info(f"BODY:\n{html_content}")
            logger.info("=========================================================")
            return False
