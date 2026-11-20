from datetime import date
import re
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped_view


def parse_date(value, field_name="data"):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"Informe uma {field_name} válida.")


def clean_text(value):
    return (value or "").strip()


def flash_form_error(message):
    flash(message, "error")


STUDENT_EMAIL_DOMAIN = "@aluno.ifal.edu.br"
CLASS_OPTIONS = ["1° ADM", "2° ADM", "3° ADM", "1° INFO", "2° INFO", "3° INFO", "1° Módulo", "2° Módulo", "3° Módulo"]

def valid_matricula(value):
    return bool(re.fullmatch(r"[0-9]{10}", value or ""))

def is_student_email(email):
    return bool(re.fullmatch(r"[^@\s]+@aluno\.ifal\.edu\.br", email or "", flags=re.IGNORECASE))


def valid_password(value):
    """Senha com pelo menos 8 caracteres, um número e um caractere especial."""
    value = value or ""
    return len(value) >= 8 and bool(re.search(r"[0-9]", value)) and bool(re.search(r"[^A-Za-z0-9\s]", value))
