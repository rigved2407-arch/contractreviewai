import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("contract-review.email")


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    if not settings.smtp_host:
        logger.warning("SMTP not configured — skipping email to %s: %s", to_email, subject)
        return False

    try:
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(text_body or html_body)
        msg.add_alternative(html_body, subtype="html")

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("Email sent to %s: %s", to_email, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


async def send_welcome_email(email: str, name: str, verify_url: str):
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto">
<h2>Welcome to Contract Review AI</h2>
<p>Hi {name},</p>
<p>Your account has been created. Please verify your email address:</p>
<p><a href="{verify_url}" style="display:inline-block;padding:12px 24px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:8px">Verify Email</a></p>
<p>Or paste this link: <a href="{verify_url}">{verify_url}</a></p>
<p>This link expires in 24 hours.</p>
<p>— The Contract Review AI Team</p>
</body></html>"""
    await send_email(email, "Welcome to Contract Review AI — Verify your email", html)


async def send_password_reset_email(email: str, name: str, reset_url: str):
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto">
<h2>Password Reset</h2>
<p>Hi {name},</p>
<p>A password reset was requested for your account. Click below to reset:</p>
<p><a href="{reset_url}" style="display:inline-block;padding:12px 24px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:8px">Reset Password</a></p>
<p>Or paste this link: <a href="{reset_url}">{reset_url}</a></p>
<p>This link expires in 1 hour. If you didn't request this, ignore this email.</p>
<p>— The Contract Review AI Team</p>
</body></html>"""
    await send_email(email, "Password Reset — Contract Review AI", html)


async def send_invoice_email(email: str, name: str, invoice_number: str, amount_inr: int, download_url: str):
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto">
<h2>Invoice #{invoice_number}</h2>
<p>Hi {name},</p>
<p>Your invoice of <strong>₹{amount_inr:,.0f}</strong> is ready.</p>
<p><a href="{download_url}" style="display:inline-block;padding:12px 24px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:8px">Download Invoice (PDF)</a></p>
<p>GST invoice with full compliance details is attached.</p>
<p>— The Contract Review AI Team</p>
</body></html>"""
    await send_email(email, f"Invoice #{invoice_number} — Contract Review AI", html)


async def send_analysis_complete_email(email: str, name: str, contract_name: str, dashboard_url: str):
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto">
<h2>Analysis Complete</h2>
<p>Hi {name},</p>
<p>AI analysis of <strong>{contract_name}</strong> is complete and ready for review.</p>
<p><a href="{dashboard_url}" style="display:inline-block;padding:12px 24px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:8px">View Results</a></p>
<p>— The Contract Review AI Team</p>
</body></html>"""
    await send_email(email, f"Analysis Complete — {contract_name}", html)
