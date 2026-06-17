import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import list

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "alert@dedolarisasi.com")

ALERT_BI = os.getenv("ALERT_EMAIL_BI", "")
ALERT_INVESTOR = os.getenv("ALERT_EMAIL_INVESTOR", "")

_smtp_ready = False


def init():
    global _smtp_ready
    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        _smtp_ready = True
        logger.info("Email client ready — SMTP %s:%d", SMTP_HOST, SMTP_PORT)
    else:
        logger.warning("SMTP not configured — email alerts disabled")


def _send(to_emails: list[str], subject: str, html_body: str):
    if not _smtp_ready or not to_emails:
        logger.warning("Cannot send email — SMTP not configured or no recipients")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, to_emails, msg.as_string())

        logger.info("Email sent to %s: %s", to_emails, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False


def send_idr_alert(currency_pair: str, cluster_label: int, is_outlier: bool,
                   volatility: float | None = None, details: dict | None = None):
    if currency_pair.upper() != "IDR":
        return False

    recipients = []
    if ALERT_BI:
        recipients.append(ALERT_BI)
    if ALERT_INVESTOR:
        recipients.append(ALERT_INVESTOR)

    if not recipients:
        return False

    level = "KRITIS" if is_outlier else "WASPADA"
    subject = f"[DEDOLARISASI] Alert {level} — IDR masuk zona rentan"

    vol_html = f"<p><b>Volatilitas:</b> {volatility:.4f}</p>" if volatility else ""
    cluster_html = f"<p><b>Cluster:</b> {cluster_label} | <b>Outlier:</b> {'Ya' if is_outlier else 'Tidak'}</p>"

    html = f"""
    <html>
    <head><style>
      body {{ font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px; }}
      .card {{ background: white; border-radius: 8px; padding: 24px; max-width: 600px; margin: auto;
              border-left: 4px solid {'#ef4444' if is_outlier else '#f59e0b'}; }}
      .header {{ font-size: 18px; font-weight: bold; margin-bottom: 16px; }}
      .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px;
                color: white; background: {'#ef4444' if is_outlier else '#f59e0b'};
                font-size: 12px; font-weight: bold; }}
      .footer {{ margin-top: 20px; font-size: 12px; color: #888; }}
    </style></head>
    <body>
      <div class="card">
        <div class="header">Alert De-Dolarisasi — IDR {level}</div>
        <p><span class="badge">{level}</span></p>
        {vol_html}
        {cluster_html}
        <p><b>Detail:</b> {details or '-'}</p>
        <div class="footer">
          Sistem Monitoring De-Dolarisasi &copy; 2026<br>
          Dikirim otomatis oleh sistem notifikasi
        </div>
      </div>
    </body>
    </html>
    """

    return _send(recipients, subject, html)


def send_custom_alert(title: str, message: str, level: str = "INFO"):
    recipients = []
    if ALERT_BI:
        recipients.append(ALERT_BI)
    if ALERT_INVESTOR:
        recipients.append(ALERT_INVESTOR)
    if not recipients:
        return False

    color = {"KRITIS": "#ef4444", "WASPADA": "#f59e0b", "INFO": "#3b82f6"}.get(level, "#3b82f6")
    subject = f"[DEDOLARISASI] {level} — {title}"

    html = f"""
    <html>
    <head><style>
      body {{ font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px; }}
      .card {{ background: white; border-radius: 8px; padding: 24px; max-width: 600px; margin: auto;
              border-left: 4px solid {color}; }}
      .header {{ font-size: 18px; font-weight: bold; margin-bottom: 16px; }}
      .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px;
                color: white; background: {color}; font-size: 12px; font-weight: bold; }}
      .footer {{ margin-top: 20px; font-size: 12px; color: #888; }}
    </style></head>
    <body>
      <div class="card">
        <div class="header">{title}</div>
        <p><span class="badge">{level}</span></p>
        <p>{message}</p>
        <div class="footer">
          Sistem Monitoring De-Dolarisasi &copy; 2026
        </div>
      </div>
    </body>
    </html>
    """

    return _send(recipients, subject, html)
