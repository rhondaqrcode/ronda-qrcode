from __future__ import annotations

from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from backend.app.core.config import settings


def send_billing_due_email(
    *,
    client_email: str,
    client_name: str,
    due_date: date,
) -> None:
    if not settings.email_host or not settings.email_user or not settings.email_password:
        raise RuntimeError("SMTP de cobranca nao configurado.")

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #172033; line-height: 1.5;">
        <div style="max-width: 640px; margin: 0 auto; border: 1px solid #d9e1ea; border-radius: 8px; padding: 24px;">
          <h2 style="margin-top: 0; color: #1f6feb;">Aviso de vencimento do servidor</h2>
          <p>Olá, {client_name}.</p>
          <p>
            Este é um lembrete amigável de que a fatura referente ao servidor do sistema
            vencerá em <strong>10 dias</strong>, na data <strong>{due_date.strftime("%d/%m/%Y")}</strong>.
          </p>
          <p>
            Para evitar a interrupção automática do sistema, pedimos que o pagamento seja
            realizado antes do vencimento.
          </p>
          <p>
            Caso o pagamento já tenha sido efetuado, por favor desconsidere este aviso.
          </p>
          <p style="margin-bottom: 0;">Atenciosamente,<br />Equipe de suporte</p>
        </div>
      </body>
    </html>
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Fatura do servidor vence em 10 dias - {due_date.strftime('%d/%m/%Y')}"
    message["From"] = settings.email_user
    message["To"] = client_email
    message.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.email_host, settings.email_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(settings.email_user, settings.email_password)
        smtp.sendmail(settings.email_user, [client_email], message.as_string())


def should_send_billing_notice(due_date: date, today: date | None = None) -> bool:
    today = today or date.today()
    return (due_date - today).days == 10


def run_billing_notice_check() -> bool:
    if not settings.billing_due_date:
        raise RuntimeError("BILLING_DUE_DATE nao configurada.")
    if not settings.billing_client_email:
        raise RuntimeError("BILLING_CLIENT_EMAIL nao configurado.")

    due_date = datetime.strptime(settings.billing_due_date, "%Y-%m-%d").date()
    if not should_send_billing_notice(due_date):
        return False

    send_billing_due_email(
        client_email=settings.billing_client_email,
        client_name=settings.billing_client_name,
        due_date=due_date,
    )
    return True
