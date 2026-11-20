import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from ..extensions import db
from ..mailer import send_verification_code
from ..models import EmailVerification, PasswordReset, User
from ..utils import CLASS_OPTIONS, STUDENT_EMAIL_DOMAIN, clean_text, is_student_email, valid_matricula, valid_password


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
CODE_LIFETIME_MINUTES = 10
CODE_RESEND_SECONDS = 60
MAX_CODE_ATTEMPTS = 5
MAX_REQUESTS_PER_IP_HOUR = 30


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _code_digest(email, code):
    key = str(current_app.secret_key).encode("utf-8")
    payload = f"{email.lower()}:{code}".encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _deliver_new_code(record, name, email, class_name):
    now = datetime.utcnow()
    if record and record.last_sent_at and now - record.last_sent_at < timedelta(seconds=CODE_RESEND_SECONDS):
        remaining = CODE_RESEND_SECONDS - int((now - record.last_sent_at).total_seconds())
        raise ValueError(f"Aguarde {max(1, remaining)} segundos antes de solicitar outro código.")

    ip_address = request.remote_addr or "desconhecido"
    recent_requests = EmailVerification.query.filter(
        EmailVerification.request_ip == ip_address,
        EmailVerification.created_at >= now - timedelta(hours=1),
    ).count()
    if recent_requests >= MAX_REQUESTS_PER_IP_HOUR:
        raise ValueError("Muitas solicitações realizadas neste computador. Tente novamente mais tarde.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    # Envia primeiro. Se o SMTP falhar, nenhum código inutilizável fica gravado.
    send_verification_code(email, code)

    if record is None:
        record = EmailVerification(email=email)
        db.session.add(record)

    record.name = name
    record.class_name = class_name or None
    record.code_hash = _code_digest(email, code)
    record.expires_at = now + timedelta(minutes=CODE_LIFETIME_MINUTES)
    record.attempts = 0
    record.request_ip = ip_address
    record.last_sent_at = now
    record.verified_at = None
    record.setup_token_hash = None
    record.setup_expires_at = None
    record.created_at = now
    db.session.commit()
    return record


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        identifier = clean_text(request.form.get("identifier") or request.form.get("email"))
        password = request.form.get("password", "")
        if identifier.isdigit():
            user = User.query.filter_by(matricula=identifier).first()
        else:
            user = db.session.query(User).filter(func.lower(User.email) == identifier.lower()).first()

        if user and user.check_password(password):
            login_user(user, remember=bool(request.form.get("remember")))
            flash(f"Olá, {user.name.split()[0]}! Seja bem-vindo(a).", "success")
            return redirect(url_for("main.dashboard"))

        flash("Matrícula/e-mail ou senha incorretos.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = clean_text(request.form.get("name"))
        email = clean_text(request.form.get("email")).lower()
        class_name = clean_text(request.form.get("class_name"))
        matricula = clean_text(request.form.get("matricula"))

        if not name or len(name) > 120:
            flash("Informe seu nome completo (até 120 caracteres).", "error")
        elif len(email) > 160 or not is_student_email(email):
            flash(f"Use um e-mail válido terminado em {STUDENT_EMAIL_DOMAIN}.", "error")
        elif not valid_matricula(matricula):
            flash("A matrícula deve conter exatamente 10 números, sem letras ou símbolos.", "error")
        elif class_name not in CLASS_OPTIONS:
            flash("Selecione uma das turmas disponíveis.", "error")
        elif User.query.filter_by(matricula=matricula).first():
            flash("Esta matrícula já possui uma conta cadastrada.", "error")
        elif EmailVerification.query.filter(EmailVerification.matricula == matricula, EmailVerification.email != email, EmailVerification.expires_at >= datetime.utcnow()).first():
            flash("Esta matrícula já está em processo de cadastro com outro e-mail.", "error")
        elif User.query.filter(func.lower(User.email) == email).first():
            flash("Já existe uma conta cadastrada com esse e-mail. Acesse a página de login.", "error")
        else:
            pending = EmailVerification.query.filter_by(email=email).first()
            try:
                pending = _deliver_new_code(pending, name, email, class_name)
                pending.matricula = matricula
                db.session.commit()
            except ValueError as error:
                flash(str(error), "error")
            except Exception:
                db.session.rollback()
                current_app.logger.exception("Falha ao enviar código de cadastro para %s", email)
                flash("Não foi possível enviar o código. Confira a configuração de e-mail do sistema ou tente novamente mais tarde.", "error")
            else:
                flash("Enviamos um código de verificação para seu e-mail institucional.", "success")
                return redirect(url_for("auth.verify_email", email=pending.email))

    return render_template("auth/register.html", class_options=CLASS_OPTIONS)


@auth_bp.route("/verificar-email", methods=["GET", "POST"])
def verify_email():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    email = clean_text(request.values.get("email")).lower()
    record = EmailVerification.query.filter_by(email=email).first() if email else None
    if not record or record.verified_at:
        flash("Solicite um novo código para continuar o cadastro.", "info")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        code = clean_text(request.form.get("code"))
        now = datetime.utcnow()
        if record.expires_at < now:
            flash("O código expirou. Solicite um novo código.", "error")
        elif record.attempts >= MAX_CODE_ATTEMPTS:
            flash("Limite de tentativas atingido. Solicite um novo código.", "error")
        elif not re.fullmatch(r"\d{6}", code) or not hmac.compare_digest(record.code_hash, _code_digest(email, code)):
            record.attempts += 1
            db.session.commit()
            remaining = max(0, MAX_CODE_ATTEMPTS - record.attempts)
            flash(f"Código incorreto. Tentativas restantes: {remaining}.", "error")
        else:
            token = secrets.token_urlsafe(32)
            record.verified_at = now
            record.setup_token_hash = _digest(token)
            record.setup_expires_at = now + timedelta(minutes=15)
            db.session.commit()
            return redirect(url_for("auth.set_password", token=token))

    return render_template("auth/verify_email.html", email=email)


@auth_bp.post("/reenviar-codigo")
def resend_code():
    email = clean_text(request.form.get("email")).lower()
    record = EmailVerification.query.filter_by(email=email).first()
    if not record or record.verified_at:
        flash("Solicite o cadastro novamente para receber um código.", "info")
        return redirect(url_for("auth.register"))

    try:
        _deliver_new_code(record, record.name, record.email, record.class_name)
    except ValueError as error:
        flash(str(error), "error")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Falha ao reenviar código para %s", email)
        flash("Não foi possível reenviar o código. Tente novamente mais tarde.", "error")
    else:
        flash("Um novo código foi enviado para seu e-mail.", "success")
    return redirect(url_for("auth.verify_email", email=email))


@auth_bp.route("/definir-senha", methods=["GET", "POST"])
def set_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    token = clean_text(request.values.get("token"))
    record = EmailVerification.query.filter_by(setup_token_hash=_digest(token)).first() if token else None
    now = datetime.utcnow()
    if not record or not record.verified_at or not record.setup_expires_at or record.setup_expires_at < now:
        flash("O link para definir a senha é inválido ou expirou. Faça o cadastro novamente.", "error")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirmation = request.form.get("confirm_password", "")
        if not valid_password(password):
            flash("A senha deve ter pelo menos 8 caracteres, um número e um caractere especial.", "error")
        elif password != confirmation:
            flash("As senhas não coincidem.", "error")
        elif User.query.filter(func.lower(User.email) == record.email).first():
            record.setup_token_hash = None
            record.setup_expires_at = None
            db.session.commit()
            flash("Já existe uma conta cadastrada com esse e-mail. Faça login.", "info")
            return redirect(url_for("auth.login"))
        else:
            user = User(name=record.name, email=record.email, role="student", class_name=record.class_name, matricula=record.matricula)
            user.set_password(password)
            db.session.add(user)
            # Mantém o registro por uma hora para contabilizar solicitações por IP,
            # mas invalida os dados temporários usados na criação da senha.
            record.setup_token_hash = None
            record.setup_expires_at = None
            record.code_hash = _code_digest(record.email, secrets.token_hex(32))
            record.expires_at = now
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Não foi possível concluir o cadastro. Talvez a conta já tenha sido criada.", "error")
                return redirect(url_for("auth.login"))
            login_user(user)
            flash("Cadastro concluído! Seu e-mail institucional foi verificado.", "success")
            return redirect(url_for("main.dashboard"))

    return render_template("auth/set_password.html", token=token, email=record.email)


def begin_password_reset(user, pending_password=None):
    """Envia código para o e-mail cadastrado. Opcionalmente deixa uma senha aguardando confirmação."""
    now = datetime.utcnow()
    record = PasswordReset.query.filter_by(user_id=user.id).first()
    if record and record.last_sent_at and now - record.last_sent_at < timedelta(seconds=CODE_RESEND_SECONDS):
        remaining = CODE_RESEND_SECONDS - int((now - record.last_sent_at).total_seconds())
        raise ValueError(f"Aguarde {max(1, remaining)} segundos antes de solicitar outro código.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    send_verification_code(user.email, code)
    if record is None:
        record = PasswordReset(user_id=user.id, code_hash="", expires_at=now, last_sent_at=now)
        db.session.add(record)
    record.code_hash = _code_digest(user.email, code)
    record.expires_at = now + timedelta(minutes=CODE_LIFETIME_MINUTES)
    record.attempts = 0
    record.last_sent_at = now
    record.reset_token_hash = None
    record.reset_token_expires_at = None
    record.pending_password_hash = generate_password_hash(pending_password) if pending_password else None
    db.session.commit()
    return record


@auth_bp.route("/recuperar-senha", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        identifier = clean_text(request.form.get("identifier"))
        user = User.query.filter_by(matricula=identifier).first() if identifier.isdigit() else db.session.query(User).filter(func.lower(User.email) == identifier.lower()).first()
        if user:
            try:
                begin_password_reset(user)
            except ValueError as error:
                flash(str(error), "error")
                return render_template("auth/forgot_password.html")
            except Exception:
                db.session.rollback()
                current_app.logger.exception("Falha ao enviar código de recuperação")
        # A mensagem não revela se matrícula ou e-mail existem no sistema.
        flash("Se os dados corresponderem a uma conta, enviaremos um código para o e-mail cadastrado.", "success")
        return redirect(url_for("auth.verify_password_reset", identifier=identifier))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/verificar-recuperacao", methods=["GET", "POST"])
def verify_password_reset():
    if current_user.is_authenticated and request.values.get("profile") != "1":
        return redirect(url_for("main.dashboard"))
    identifier = clean_text(request.values.get("identifier"))
    user = User.query.filter_by(matricula=identifier).first() if identifier.isdigit() else db.session.query(User).filter(func.lower(User.email) == identifier.lower()).first()
    record = PasswordReset.query.filter_by(user_id=user.id).first() if user else None
    if not record:
        flash("Não há uma recuperação válida. Solicite um novo código.", "info")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        code = clean_text(request.form.get("code"))
        now = datetime.utcnow()
        if record.expires_at < now:
            flash("O código expirou. Solicite outro código.", "error")
        elif record.attempts >= MAX_CODE_ATTEMPTS:
            flash("O limite de tentativas foi atingido. Solicite outro código.", "error")
        elif not re.fullmatch(r"\d{6}", code) or not hmac.compare_digest(record.code_hash, _code_digest(user.email, code)):
            record.attempts += 1
            db.session.commit()
            flash("Código incorreto. Confira o e-mail e tente novamente.", "error")
        elif record.pending_password_hash:
            user.password_hash = record.pending_password_hash
            db.session.delete(record)
            db.session.commit()
            flash("Senha alterada após confirmação por e-mail.", "success")
            return redirect(url_for("main.account") if current_user.is_authenticated else url_for("auth.login"))
        else:
            token = secrets.token_urlsafe(32)
            record.reset_token_hash = _digest(token)
            record.reset_token_expires_at = now + timedelta(minutes=15)
            # Invalida o código de seis dígitos após a confirmação; o token passa a ser a única autorização.
            record.code_hash = _code_digest(user.email, secrets.token_hex(32))
            record.attempts = MAX_CODE_ATTEMPTS
            db.session.commit()
            return redirect(url_for("auth.reset_password", token=token))
    return render_template("auth/verify_password_reset.html", identifier=identifier, email=user.email)


@auth_bp.route("/nova-senha/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    token = clean_text(token)
    record = PasswordReset.query.filter_by(reset_token_hash=_digest(token)).first()
    now = datetime.utcnow()
    if not record or not record.reset_token_expires_at or record.reset_token_expires_at < now:
        flash("O acesso para redefinir a senha é inválido ou expirou. Solicite outro código.", "error")
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        confirmation = request.form.get("confirm_password", "")
        if not valid_password(password):
            flash("Use pelo menos 8 caracteres, incluindo um número e um caractere especial.", "error")
        elif password != confirmation:
            flash("As senhas não coincidem.", "error")
        else:
            record.user.set_password(password)
            db.session.delete(record)
            db.session.commit()
            flash("Senha redefinida com sucesso. Entre com sua nova senha.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", token=token)


@auth_bp.post("/logout")
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))
