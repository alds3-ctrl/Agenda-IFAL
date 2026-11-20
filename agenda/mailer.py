import smtplib
from email.message import EmailMessage

from flask import current_app


def send_verification_code(recipient, code):
    """Envia o código por SMTP. As credenciais vêm somente do ambiente/.env."""
    server = current_app.config.get("MAIL_SERVER")
    username = current_app.config.get("MAIL_USERNAME")
    password = current_app.config.get("MAIL_PASSWORD")
    sender = current_app.config.get("MAIL_DEFAULT_SENDER") or username
    if not all([server, username, password, sender]):
        raise RuntimeError("O envio de e-mail ainda não foi configurado no arquivo .env.")

    message = EmailMessage()
    message["Subject"] = "Código de verificação — Agenda IFAL"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Olá!\n\n"
        "Use o código abaixo para confirmar seu e-mail institucional e criar sua conta no Agenda IFAL:\n\n"
        f"{code}\n\n"
        "O código expira em 10 minutos e só pode ser usado uma vez. Não compartilhe este código.\n\n"
        "Se você não solicitou este cadastro, ignore esta mensagem.\n\n"
        "Agenda IFAL — IFAL Campus Viçosa"
    )

    port = int(current_app.config.get("MAIL_PORT", 587))
    timeout = int(current_app.config.get("MAIL_TIMEOUT", 15))
    use_ssl = current_app.config.get("MAIL_USE_SSL", False)
    use_tls = current_app.config.get("MAIL_USE_TLS", True)

    if use_ssl:
        with smtplib.SMTP_SSL(server, port, timeout=timeout) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(server, port, timeout=timeout) as smtp:
            smtp.ehlo()
            if use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(message)
